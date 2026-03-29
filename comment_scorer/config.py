from dataclasses import dataclass
import os


@dataclass
class AppConfig:
    api_key: str
    base_url: str = "https://ai.hackclub.com/proxy/v1"
    model: str = "deepseek/deepseek-v3.2"
    timeout_seconds: int = 30
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            api_key=os.getenv("HACKCLUB_API_KEY", "").strip(),
            base_url=os.getenv("HACKCLUB_BASE_URL", "https://ai.hackclub.com/proxy/v1").strip(),
            model=os.getenv("HACKCLUB_MODEL", "deepseek/deepseek-v3.2").strip(),
            timeout_seconds=int(os.getenv("HACKCLUB_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("HACKCLUB_MAX_RETRIES", "2")),
        )

