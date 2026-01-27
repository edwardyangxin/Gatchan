# Gatchan

Telegram bot to capture notes (text, links, voice memos, shares) and create Todoist subtasks under a main "todo later" task.

## MVP Scope
- Inputs: text messages, links, forwarded/share text, voice memos, images (URL stored in task description)
- Output: subtask created under a fixed parent task in Todoist
- Optional: voice memo transcription via cloud API

## Setup
1. Create a Telegram Bot via BotFather, get `TELEGRAM_BOT_TOKEN`.
2. Create a Todoist API token, get `TODOIST_API_TOKEN`.
3. Set the main task name for "todo later", set `TODO_LATER_TASK_NAME` (created if missing).
4. Set a webhook secret token, `TELEGRAM_WEBHOOK_SECRET`, and register it with Telegram.
5. (Optional) For voice memos, set `TRANSCRIBE_PROVIDER` and a provider API key.
6. (Optional) Set whitelist envs to restrict who can talk to the bot.

## Environment Variables
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_ALLOWED_USER_IDS` (optional, comma-separated user IDs)
- `TELEGRAM_ALLOWED_CHAT_IDS` (optional, comma-separated chat IDs; groups/channels are negative)
- `TELEGRAM_WHITELIST_REPLY` (optional, `true` to reply on denial)
- `TODOIST_API_TOKEN`
- `TODO_LATER_TASK_NAME`
- `TRANSCRIBE_PROVIDER` (optional, `openai` or `gemini`)
- `OPENAI_API_KEY` (if using OpenAI/Whisper)
- `GEMINI_API_KEY` (if using Gemini)

## Secrets handling
- Copy `.env.example` to `.env` locally; never commit `.env`.
- Rotate tokens by revoking them at the provider and updating the env vars.
- Avoid logging secrets or full webhook payloads.

## Development workflow
- Select an issue from the Project board Backlog.
- Move the issue to In progress when you start work.
- Open a PR and move the issue to In review.
- Merge the PR and move the issue to Done.

## Local development
1. Create a virtualenv and install dependencies:
   - `python -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt -r requirements-dev.txt`
2. Copy `.env.example` to `.env` and fill in values.
3. Run the server:
   - `uvicorn app.main:app --reload --port 8000`
4. Health check:
   - `curl http://localhost:8000/health`

## Cloud Run notes
- Set the container port to `8000`.
- Ensure `TELEGRAM_WEBHOOK_SECRET` matches the secret passed to Telegram when setting the webhook.
- Webhook endpoint is `POST /webhook` with header `X-Telegram-Bot-Api-Secret-Token`.

### Current Cloud Run deployment
- Project ID: `home-inventory-483623` (display name: `home-inventory`)
- Region: `us-central1`
- Service: `gatchan-bot-webhook`
- Health check: `GET /health`

### Cloud Run deploy (example)
```bash
gcloud run deploy gatchan-webhook \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars TELEGRAM_BOT_TOKEN=...,TELEGRAM_WEBHOOK_SECRET=...,TODOIST_API_TOKEN=...,TODO_LATER_TASK_NAME=...
```

### Telegram webhook registration (example)
```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://YOUR_CLOUD_RUN_URL/webhook" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

## Notes
- This repo is currently a scaffold. Implementation plan will be added next.

## Project Board
- Backlog and collaboration board: https://github.com/users/edwardyangxin/projects/1/
