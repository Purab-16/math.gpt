# Project Rules

## Project
math.gpt: a math solver web app. FastAPI + Gemini API. Plain HTML/CSS/JS frontend.

## Safety
- Never read, open, or print the .env file.
- Never run git commit, git push, or git config.
- Never run pip install. Ask me first.
- Never put API keys in code.
- Do not edit .claude/ or .githooks/.

## Code rules
- Beginner friendly code. Comments and docstrings in English.
- Do not add libraries without asking.
- Do not add thinking_config to the Gemini config.
- Return generic errors to users. No stack traces or raw model output.
- Do not log API keys, user text, or image bytes.

## Output rules
- Keep answers short. No long explanations.
- Change only the files I mention.
- At the end, list changed files and how to test.
