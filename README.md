# Gatchan

Telegram bot to capture notes (text, links, voice memos, shares) and create Todoist subtasks under a main "todo later" task.

## MVP Scope
- Inputs: text messages, links, forwarded/share text, voice memos
- Output: subtask created under a fixed parent task in Todoist
- Optional: voice memo transcription via cloud API

## Setup (planned)
1. Create a Telegram Bot via BotFather, get `TELEGRAM_BOT_TOKEN`.
2. Create a Todoist API token, get `TODOIST_API_TOKEN`.
3. Identify the parent task ID for "todo later", set `TODO_LATER_TASK_ID`.
4. (Optional) For voice memos, set a transcription provider API key.

## Environment Variables (planned)
- `TELEGRAM_BOT_TOKEN`
- `TODOIST_API_TOKEN`
- `TODO_LATER_TASK_ID`
- `TRANSCRIBE_PROVIDER` (optional, e.g. `openai`)
- `OPENAI_API_KEY` (if using OpenAI/Whisper)

## Notes
- This repo is currently a scaffold. Implementation plan will be added next.
