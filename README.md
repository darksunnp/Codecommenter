# Code Comment Quality Scorer

Comment quality platform with both CLI and web experience. It evaluates how useful and accurate a comment/docstring is for a function.

## Features

- Judge pass scores each comment on:
	- accuracy
	- completeness
	- clarity
- Critique pass reviews the first judgment and adjusts scores.
- Confidence score is derived from agreement between judge and critique.
- Single-record and batch JSONL scoring modes.
- Modern web app UI with animated controls.
- Client-side encrypted API key vault in the browser.

## Setup

1. Activate your virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables in your shell:

```powershell
$env:HACKCLUB_API_KEY="your_key"
$env:HACKCLUB_BASE_URL="https://ai.hackclub.com/proxy/v1"
$env:HACKCLUB_MODEL="deepseek/deepseek-v3.2"
$env:HACKCLUB_TIMEOUT_SECONDS="30"
$env:HACKCLUB_MAX_RETRIES="2"
```

## Usage

### Web Platform (recommended)

Run the web app:

```bash
python main.py web --host 127.0.0.1 --port 8000 --reload
```

Then open:

- http://127.0.0.1:8000

### Deploy On Vercel

This repository is now preconfigured for Vercel deployment with:

- `api/index.py` as the serverless entrypoint
- `vercel.json` routing all paths to the FastAPI app
- static files from `web/` included in the function bundle

Steps:

1. Install Vercel CLI:

```bash
npm i -g vercel
```

2. From the project root, log in:

```bash
vercel login
```

3. Deploy preview:

```bash
vercel
```

4. Deploy production:

```bash
vercel --prod
```

5. Open the generated URL from Vercel output.

Notes for Vercel:

- This app accepts the Hack Club API key per request from the client-side vault.
- You do not need to store user API keys in Vercel environment variables.
- If function timeouts occur for dual-pass scoring, use fast mode in the UI or upgrade function limits.
- API docs will be available at `/api/docs` on your deployed domain.

How key security works in web mode:

- You enter your own Hack Club API key in the vault gate.
- The key is encrypted in your browser using your passphrase (AES-GCM via Web Crypto API).
- The encrypted blob is stored in localStorage on your device.
- The backend receives your key only per scoring request and does not store it.

Security note:

- This is secure at rest in browser storage, but any key used for live requests must be decrypted in memory during your session.
- For highest safety, use a strong passphrase and avoid shared devices.

### CLI

Single sample:

```bash
python main.py score \
	--language python \
	--function-text "def add(a, b): return a + b" \
	--comment-text "Adds two numbers and returns the sum" \
	--output json
```

Batch sample from JSONL:

```bash
python main.py batch --input samples.jsonl --output-file results.jsonl
```

Each JSONL input line should be a JSON object like:

```json
{"language":"python","function_code":"def add(a,b): return a+b","comment_text":"Adds two numbers","context":""}
```

## Run Tests

```bash
pytest
```

## Notes

- Use `--fast` to skip critique pass for cheaper/faster runs.
- The scorer is language-agnostic in v1 and evaluates plain text/code as provided.
- Web API docs are available at `/api/docs` while the server is running.

