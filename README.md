# Gatchan

Telegram bot to capture notes (text, links, voice memos, shares) and create Todoist subtasks under a main "todo later" task.

## MVP Scope
- Inputs: text messages, links, forwarded/share text, voice memos
- Output: subtask created under a fixed parent task in Todoist
- Optional: voice memo transcription via cloud API

## Setup
1. Create a Telegram Bot via BotFather, get `TELEGRAM_BOT_TOKEN`.
2. Create a Todoist API token, get `TODOIST_API_TOKEN`.
3. Identify the parent task ID for "todo later", set `TODO_LATER_TASK_ID`.
4. (Optional) For voice memos, set `TRANSCRIBE_PROVIDER` and a provider API key.

## Environment Variables
- `TELEGRAM_BOT_TOKEN`
- `TODOIST_API_TOKEN`
- `TODO_LATER_TASK_ID`
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

## Notes
- This repo is currently a scaffold. Implementation plan will be added next.

## Project Board
- Backlog and collaboration board: https://github.com/users/edwardyangxin/projects/1/
