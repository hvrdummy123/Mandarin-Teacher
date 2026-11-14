# Product specification — duihua · 对话

Personal Mandarin speaking coach for a single learner on their own machine.

This document is the product and engineering source of truth for scope, behaviour, and stack. Smaller implementation choices are logged in [`DECISIONS.md`](DECISIONS.md). System shape and rationale live in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 1. Product overview

### Audience

One user: someone who already studies Mandarin in apps (Duolingo, Airlearn, etc.) but has almost nobody to speak with. The app is their daily speaking partner.

### Promise

Talk to an AI in Mandarin by voice, see both sides transcribed with pinyin, hanzi, and English, look up any word instantly, get light grammar corrections and (later) tone feedback, and practise at a chosen level and topic — without it feeling slow.

### Constraints

- Single user, local machine or VM. No signup, no multi-tenancy.
- Default config stays free: free-tier APIs and/or local models. No paid service required to run.
- Daily-driver quality: fast enough for short morning practice sessions.

### Out of scope

Accounts, social features, leaderboards, payments, push notifications, native mobile apps, spaced-repetition engines, and lesson-content authoring tools.

---

## 2. Features

### 2.1 Implemented / in active use

| Feature | Description |
| --- | --- |
| **Voice conversation** | Tap-to-talk mic (hands-free optional). Speech is transcribed; the AI replies in text and audio. Live captions while speaking. |
| **Rich transcript** | Stacked pinyin, hanzi, and English per bubble. Toggles for each layer. Tone-coloured pinyin. |
| **Word lookup & save** | Click/tap a word for definitions, HSK level, character breakdown, TTS replay, and save to a personal list. |
| **Levels 1–100** | Tier picker (1–10) plus fine level slider. Level guides vocabulary and reply complexity. |
| **Topics** | Scenario role-play (~30 topics). AI opens in character; user practises toward a stated goal. |
| **Free chat** | Open conversation at the current level without a scenario. |
| **Corrections** | After a user turn, optional “I think you meant…” with a more natural line and a short reason. |
| **Review before send** | Optional gate: confirm or discard the transcript (with enrich/repair) before calling the AI. |
| **Saved words** | Searchable list with context sentence; delete supported. |
| **Progress (light)** | XP / streak / daily goal surface; full gamification rules continue to mature. |

### 2.2 Planned

| Feature | Description |
| --- | --- |
| **Image practice** | Upload/paste an image; OCR Chinese text; describe and ask level-appropriate questions answered by voice or text. |
| **Pronunciation & tone feedback** | Per-syllable tone verdicts and overall score from audio (not STT alone). |
| **Read-aloud mode** | Native TTS prompt → user records → tone report → retry. |
| **Full XP system** | Complete awards, streak rules, and level-up suggestions based on recent quality. |

---

## 3. Architecture (summary)

Hexagonal layout: React SPA ↔ FastAPI (REST + WebSocket) ↔ application use cases ↔ pure domain ↔ ports implemented by adapters (LLM, STT, TTS, dictionary, SQLite).

```
Browser (React / Vite / Zustand)
  │ REST                    │ WebSocket (PCM + events)
  ▼                         ▼
FastAPI  api/ → application/ → domain/
                ports ← adapters (LLM chain, Whisper, Edge TTS, CEDICT, DB)
```

Design goals for this shape:

- Swap Gemini / OpenRouter / Ollama without rewriting chat.
- Keep linguistic enrichment (pinyin, dictionary) local and deterministic.
- Survive free-tier 429s via ordered fallback, breakers, and clear retry UX — never fake AI replies.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for diagrams, trade-offs, and improvement paths.

### Voice turn (hot path)

```
mic → AudioWorklet (16 kHz PCM) → WebSocket
  → VAD (hands-free) or user end (tap mode)
  → STT (browser hint preferred, else Whisper) → optional topic repair
  → parallel: LLM reply → sentence TTS
              LLM analysis (translation, correction)
  → local TextAnalyzer (jieba + pypinyin + CEDICT)
  → persist + XP
```

**Latency targets** (measured by `scripts/bench_latency.py`): end of speech → first reply audio &lt; 3.0 s on a modern laptop; STT of ~5 s speech &lt; 1.5 s; first LLM token &lt; 1.5 s on a free API when healthy.

WebSocket carries JSON control events (`session.start`, `turn.start`, `turn.end`, `transcript.user`, `reply.*`, `analysis`, `error`, …) plus binary PCM up and audio down. Schema: `backend/app/api/ws_schema.py` (TypeScript types generated from the same source).

---

## 4. Tech stack

| Area | Choice |
| --- | --- |
| Backend | FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, Alembic, httpx, structlog, `uv` |
| Speech | faster-whisper, energy/VAD, edge-tts (+ disk cache); browser SpeechRecognition for live captions |
| Linguistics | jieba, pypinyin, CC-CEDICT, HSK word list |
| Frontend | React 18, Vite, TypeScript (strict), Tailwind, Zustand |
| Data | SQLite (WAL); app DB separate from dictionary DB |
| LLMs | Gemini, OpenRouter (`:free` or paid), optional Ollama — selected via `LLM_PROVIDERS` |

**Explicitly avoided:** LangChain/LlamaIndex, Redis, Celery, Postgres (for this single-user app), auth frameworks, UI component kits, analytics.

Config is `pydantic-settings` from `.env`. Secrets stay out of git; `.env.example` documents keys and model ids (free-tier names change — verify against provider docs).

---

## 5. Repository layout

```
duihua/
  README.md  SPEC.md  DECISIONS.md  TEST_REPORT.md
  Makefile  .env.example  pyproject.toml
  docs/ARCHITECTURE.md  docs/portfolio/
  scripts/   fetch_data.py  bench_latency.py  portfolio/ …
  backend/app/
    api/  application/  domain/  ports/  adapters/  resilience/  prompts/
    migrations/  tests/
  frontend/src/
    app/  components/  features/  lib/  styles/
    tests/
```

---

## 6. Data model (SQLite)

**App DB (`data/duihua.db`)**

- `sessions` — mode, topic, level, timestamps  
- `messages` — role, text, pinyin JSON, translation, optional `audio_path`  
- `corrections` — original / better / reason  
- `pronunciation_attempts` — scores and syllable JSON (for tone phase)  
- `saved_words` — word, pinyin, definition, HSK, context  
- `xp_events`, `daily_stats` — progress  
- `settings` — level, UI prefs, speech options  
- `provider_usage` — per-provider daily usage / last error  

**Dictionary DB (`data/dictionary.db`)**

- `cedict` — simplified, traditional, pinyin, definitions  
- `hsk` — word → level  

Schema changes go through Alembic. Index only where queries need it.

---

## 7. Rich transcript

- **Backend `TextAnalyzer`:** jieba segmentation, pypinyin (tone marks + sandhi), CEDICT lookup, HSK attach. Returns tokens `{surface, pinyin, definitions[], hsk, chars[]}`. Never an LLM call.
- **Frontend:** `<ruby>` rendering; tone colours (1–4 + neutral) with a second cue for colour-blind users.
- **Popover / side panel:** up to three definitions, HSK badge, character breakdown, hear word / hear sentence, Save.
- **Toggles:** pinyin, hanzi, English. Out-of-level AI words get a dotted underline.

---

## 8. Levels (1–100)

- `data/level_curve.json` (and formula defaults) define vocabulary size, max sentence length, grammar hints, and speech-rate guidance per level.
- Tier 1–10 jumps to the tier’s first level; the fine slider moves within the tier.
- System prompts include level rules, topic/role, a compact vocab hint (HSK band + sample + recent saved words) — not the full lexicon.
- **Post-check:** after a reply, measure share of words above the level cutoff (topic keywords and proper nouns exempt). Above threshold (default 12%), regenerate once with violators forbidden; if still over, accept and mark out-of-level.

Suggested level changes (offer, don’t force) based on recent turn quality are part of the progress roadmap.

---

## 9. Topics

Stored in topics data (e.g. `data/topics.json` / domain loaders). Each topic has: `id`, `title_en`, `title_zh`, `ai_role`, `scenario`, `user_goal`, `keywords[]`, `min_level`.

Coverage includes everyday situations such as: restaurant, cafe, street food, grocery and clothes shopping, introductions, family, friends/plans, weather, directions, taxi, metro, airport, hotel, phone bookings, doctor/pharmacy, payments, phone/internet issues, job interview, office, studying, hobbies, sports, media, cooking, festivals, renting, travel, news/opinions, technology.

In role-play the AI stays in character, nudges toward the user goal, and only breaks character to correct. `min_level` soft-warns when the learner’s level is below the topic’s.

Topic openings may be canned for instant start; subsequent turns use the LLM. Topic keywords also bias STT repair for common near-homophone mistakes.

---

## 10. Pronunciation and tone scoring (planned)

Honest, local, rule-based feedback — limits called out in UI and README.

STT alone is not enough: Whisper often “autocorrects” wrong tones into valid words. Scoring should work on **audio** (F0 via Parselmouth, speaker-normalised, aligned to syllables, compared to tone templates).

`PronunciationScorer` remains a Protocol so a cloud scorer could be added later; the first implementation is local.

Read-aloud mode: show a sentence → play TTS → record → report → retry; store attempts.

---

## 11. Points system

Domain rules (unit-tested as they land):

- XP for turns spoken, length (capped), clean turns, saved words, strong tone scores, completed topic goals.
- Daily goal (default 100 XP); streak from consecutive days meeting a minimum.
- All knobs in one `xp_rules` config; events written to `xp_events` and shown with a light toast.

---

## 12. UI and design

**Feel:** calm, warm, slightly bookish — a morning practice tool, not a SaaS dashboard.

| Token | Light | Notes |
| --- | --- | --- |
| Paper | `#F6F1E7` | Background |
| Ink | `#1F1B16` | Text |
| Vermilion | `#C8372D` | Accent |
| Jade | `#3F7D6B` | Secondary |
| Muted | `#8A8173` | Secondary text |

Dark theme: warm charcoal background with softened accents. Honour `prefers-color-scheme` and a manual toggle.

- Type: serif for brand/hanzi feel; clear UI sans; hanzi in bubbles ≥ 22px; pinyin ~0.55×.
- Layout: left rail (Chat / Topics / Saved words / Progress), centre conversation, right details drawer. Mobile: single column, large mic.
- Mic: prominent control with listening / thinking / speaking states.
- Copy: English-first chrome with optional Chinese labels; short, human error messages.
- A11y: keyboard path, focus rings, ARIA, contrast AA. Respect `prefers-reduced-motion`.
- Perf target: JS bundle under ~250 KB gzipped where practical.

---

## 13. Engineering standards

- Python 3.11+ (project pins 3.12), TypeScript strict.
- Ruff + mypy on backend; ESLint + `tsc` on frontend.
- CI: lint, types, unit/integration, frontend tests.
- Health: `/healthz`, `/readyz` (DB, Whisper, dictionary, at least one LLM configured).
- Observability: structured logs with turn ids; stage timings; `GET /api/debug/timings`.
- Security/privacy defaults: bind `127.0.0.1`, tight CORS, upload caps (images ≤ 8 MB, re-encoded, EXIF stripped), audio turns capped (~60 s).
- Microphone note: browsers require `localhost` or HTTPS; use SSH port-forward from a VM (documented in README).

Dependency budget stays tight: only stack items above, plus at most a couple of small frontend utilities if justified in `DECISIONS.md`. Prefer functions over ceremony; ports exist so vendors stay replaceable.

---

## 14. Roadmap

| Phase | Focus | Status |
| --- | --- | --- |
| **P0** | Scaffold, config, DB, health, empty shell | Done |
| **P1** | Text chat, rich transcript, hover/save, levels/topics, corrections | Done |
| **P2** | Voice (WS, STT, TTS), English UI, four screens, review-before-send, topic repair | Done / iterating |
| **P3** | Full XP, streak, settings persistence, level suggestions | Partial |
| **P4** | Image practice (OCR + vision Q&A) | Planned |
| **P5** | Local tone scorer + read-aloud | Planned |
| **P6** | Hardening, benches, docs polish, failure drills | Ongoing |

---

## 15. Testing strategy

| Layer | What we cover |
| --- | --- |
| **Unit** | Pinyin/sandhi, dictionary, level post-check, XP rules, resilience (retry/breaker/quota/fallback), transcript repair |
| **Integration** | REST chat flows with FakeLLM; WS voice with fixtures; migrations; readiness |
| **Frontend** | Component tests (ruby, shell); Playwright checklist for navigation and mic-primary chrome |
| **Perf** | `bench_latency.py` — p50/p95 for STT, LLM, TTS, end-to-end |
| **Human** | Checklist for naturalness, level feel, hover usefulness, long sessions |

Results and “could not verify” notes go in [`TEST_REPORT.md`](TEST_REPORT.md). Automation cannot fully judge accent handling or whether tone tips match a native speaker — those stay on the human checklist.

---

## 16. LLM prompts

Versioned under `backend/app/prompts/`:

- **Reply** — patient Mandarin partner; stay at level; short turns; topic role; no pinyin/English in the model output (the app adds those).
- **Analysis** — JSON only (`translation_en`, correction, goal progress, suggested words); validated; one repair attempt on bad JSON.
- **Image** (planned) — simple Chinese + English description, visible text, graded questions.

Templates use explicit variables; keep them short.

---

## 17. Definition of done (release checklist)

- Fresh clone: `make setup && make data && make dev` works; README covers mic/SSH notes.
- Features in §2.1 behave end to end on a real machine.
- Tests green, or gaps listed honestly in `TEST_REPORT.md`.
- Latency budgets met or explained.
- Runs with free Gemini and/or OpenRouter and/or local Ollama — no paid dependency in defaults.
- Lint/types clean; `DECISIONS.md` and `docs/ARCHITECTURE.md` match reality.
