from __future__ import annotations

import time
from typing import Any
import requests

from .config import AppConfig

class HackClubClientError(RuntimeError):
    pass

class HackClubClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.session = requests.Session()
        self.endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        if not self.config.api_key:
            raise HackClubClientError("Missing HACKCLUB_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                return _extract_message_content(response.json())
            except requests.HTTPError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise HackClubClientError(f"HTTP error: {e}")
            except requests.Timeout:
                last_error = requests.Timeout("Request timed out")
                if attempt < self.config.max_retries:
                    # wait 1s, then 2s before retrying
                    time.sleep(2 ** attempt)
                    continue
                raise HackClubClientError("Request timed out after all retries")
            except requests.RequestException as e:
                last_error = e
                if attempt < self.config.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise HackClubClientError(f"Request failed: {e}")

        raise HackClubClientError(f"Request failed after retries: {last_error}")


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise HackClubClientError("Response did not include choices")

    message = choices[0].get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    parts.append(str(text))
        if parts:
            return "\n".join(parts)

    raise HackClubClientError("Unsupported response content format")
