# 对话 (duihua)

I built this because I study Mandarin in apps but have almost nobody to speak with. This is a local speaking partner: voice in Mandarin, live transcript with pinyin and meanings, tone feedback, and light corrections. One user, on your own machine, free-tier or local models only.

## Status

**Phase 2 (voice + English UI)** works: English-first chrome (optional Chinese labels), four screens (Chat / Topics / Saved words / Progress), mic-primary input with text fallback, topic role-play with AI opening first, WebSocket voice (VAD + Whisper + TTS). Tone scoring is still Phase 5; spoken audio is saved for later.

UI copy is English by default. Use **Hide Chinese labels** if you only want English.

## Setup

Needs Python 3.11+, [uv](https://docs.astral.sh/uv/), and Node 20+.

```bash
make setup          # uv sync, npm install, copy .env, migrate
make data           # download CC-CEDICT + HSK list into data/dictionary.db (needs network)
# edit .env — add a free Gemini API key when you want LLM replies
make dev            # API on :8000, Vite on :5173
```

Open http://127.0.0.1:5173. Browsers only allow the microphone on `localhost` or HTTPS. If the app runs on a remote VM, SSH-forward the port instead of exposing it:

```bash
ssh -L 5173:127.0.0.1:5173 -L 8000:127.0.0.1:8000 user@vm
```

Then use http://127.0.0.1:5173 on your laptop.

## Checks

```bash
make test
make lint
```

## Attribution

- Dictionary: [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) (Creative Commons Attribution-ShareAlike 4.0)
- HSK list: [drkameleon/complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary) (MIT); falls back to a tiny seed list if offline


## Known limits (honest)

Tone scoring will be rule-based and approximate. Free-tier rate limits will bite. Accents and overlapping speech will confuse STT. None of that is built yet — this commit is the scaffold only.
