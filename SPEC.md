# SPEC: 对话 (duihua), a personal Mandarin speaking coach

You are a senior engineer building this project end to end in this repository. Read this whole document before writing any code. It is the single source of truth. Where it is silent, make the smallest sensible decision and record it in `DECISIONS.md` (one line each). Do not stop to ask questions.

---

## 0. Working rules (read first)

1. **Build in the phases of section 14, in order.** After each phase: run that phase's tests, fix failures, commit with a normal human-sounding message, then continue. Do not start a phase with red tests.
2. **No bloat.** Only build what this document lists. No extra pages, no analytics, no auth system, no admin panel, no plugin framework, no "future-proofing" abstractions beyond the ports in section 4. Every dependency must earn its place; the dependency budget is in section 13. Delete dead code before finishing.
3. **Free only.** Nothing in the default configuration may require a paid service or a credit card. Every external provider sits behind an adapter and is selected by config.
4. **Never weaken a test to make it pass.** If a test fails, fix the code. If a test is genuinely wrong, fix it and explain why in `DECISIONS.md`.
5. **Do not fake results.** If something cannot be verified in this environment (real microphone, real GPU, network-limited provider), say so in `TEST_REPORT.md` instead of claiming it passed.
6. Python 3.11+, TypeScript strict mode. Everything typed. Formatting and linting enforced by tooling (section 12).

---

## 1. Product

**Who it's for:** exactly one user, a learner of Mandarin who already studies vocabulary in apps (Duolingo, Airlearn) but has nobody to speak with. This app is her speaking partner.

**Core promise:** talk to an AI in Mandarin, by voice, and see both sides transcribed live with pinyin, hanzi and instant word meanings. Get real feedback on grammar and on tones. Practise at a chosen level and topic. Use daily without it feeling slow.

**Constraints:**
- Single user, runs on her own machine (or VM). No signup, no multi-tenancy.
- Zero running cost. Free-tier or local models only; different models for different jobs is fine.
- Fast, correct, efficient. Daily-driver quality.

### Features (this is the complete list)

1. **Voice conversation.** Push-to-talk and hands-free modes. The user's speech is transcribed; the AI replies in text and in speech; both are shown as live transcripts.
2. **Rich transcript.** Every Chinese message shows hanzi, pinyin (ruby text above each character), and an English translation that can be toggled. Hovering (or tapping on touch) any word shows: pinyin, English definitions, HSK level, and per-character meaning. One click saves the word.
3. **Levels 1 to 100.** Fine-grained difficulty. The UI also exposes a coarse 10-tier picker (each tier = 10 levels). Level controls vocabulary range, sentence length and grammar complexity (section 7).
4. **30 topics** (section 8). Each is a scenario with a role for the AI and a goal for the user.
5. **Conversation modes:** Free chat, Topic role-play, Image practice, Read-aloud (tone drills).
6. **Image practice.** Upload or paste an image. The app extracts any Chinese text (OCR), explains what the image shows, and can generate questions about it that the user answers by voice or text.
7. **Pronunciation and tone feedback.** After the user speaks, show per-syllable tone verdicts and an overall score (section 9).
8. **Corrections.** After each user turn, a subtle correction card: what they said, a more natural version, a one-line reason.
9. **Points system.** XP, daily goal, streak, level progress (section 10).
10. **Saved words.** A simple list of words saved from hover, with their context sentence. No spaced repetition engine. Keep it a list with search and delete.

Not features: accounts, social, leaderboards, payments, notifications, mobile apps, flashcard engine, lesson content authoring.

---

## 2. Architecture overview

Layered, hexagonal ("ports and adapters"). Business logic never imports a vendor SDK.

```
Browser (React SPA, PWA-installable)
  │  REST (JSON)           WebSocket (voice turn stream)
  ▼
FastAPI app ── api layer (routers, schemas, WS handler)
  │
  ├─ application layer (use cases: StartSession, RunVoiceTurn, AnalyseImage, ScorePronunciation, AwardXP ...)
  │
  ├─ domain layer (pure Python: Level policy, Vocabulary, XP rules, Tone model, Correction model)
  │
  └─ adapters (implement ports)
       ├─ LLMProvider:     GeminiAdapter | OpenRouterAdapter | OllamaAdapter  (+ FallbackChain)
       ├─ STTProvider:     FasterWhisperAdapter | (BrowserSTT handled client-side as optional fast path)
       ├─ TTSProvider:     EdgeTTSAdapter (+ disk cache)
       ├─ OCRProvider:     RapidOCRAdapter
       ├─ VisionProvider:  GeminiVisionAdapter (via LLMProvider with image input)
       ├─ PronunciationScorer: LocalToneScorer  (Protocol allows a cloud scorer later)
       ├─ DictionaryRepo:  CedictSqliteRepo
       └─ Persistence:     SQLite via SQLAlchemy 2.x + Alembic migrations
```

Rules:
- Dependencies point inward. `domain` imports nothing from `adapters` or `api`.
- Ports are `typing.Protocol` classes in `app/ports/`. Wiring happens in one composition root (`app/container.py`), not via a DI framework.
- Every outbound call has a timeout, bounded retries with jitter, and a circuit breaker (hand-rolled, about 60 lines; do not add a library for it).
- LLM calls go through a `FallbackChain`: ordered providers from config, automatic failover on timeout, 429 or 5xx, with a per-provider quota tracker (table `provider_usage`) so free-tier limits are respected before they are hit.
- Config via `pydantic-settings` from `.env`. No secrets in the repo. `.env.example` is committed.
- Structured JSON logging with a request/turn id on every line. Per-stage timings (stt_ms, llm_first_token_ms, tts_first_byte_ms, total_ms) are logged for every voice turn and exposed at `GET /api/debug/timings` (last 50 turns).
- Health: `GET /healthz` (process up) and `GET /readyz` (DB reachable, Whisper model loaded, dictionary loaded, at least one LLM provider configured).
- Bind to `127.0.0.1` by default. CORS restricted to the dev origin. Upload limits: images max 8 MB, jpeg/png/webp only, re-encoded server-side and EXIF stripped; audio frames capped per turn (60 s).
- Note in README: browsers only allow microphone access on `localhost` or HTTPS. If running on a remote VM, use an SSH port-forward to localhost instead of exposing the port.

### Voice turn pipeline (the hot path, optimise this)

```
mic → AudioWorklet (16 kHz mono PCM, 20 ms frames) → WS binary frames
   → server VAD (Silero via onnxruntime, or webrtcvad if lighter) detects end of speech
   → faster-whisper (small, int8, CPU, language="zh", beam_size=1) → user transcript
   → [parallel]
        A) LLM reply stream (plain text, no JSON) → split at sentence punctuation → each sentence to TTS immediately → audio chunks to client
        B) LLM analysis call (JSON: translation, correction, new-word hints) → sent when ready
        C) LocalToneScorer on the same audio buffer → tone report
   → server computes pinyin + word segmentation + dictionary lookups for each message (no LLM)
   → XP awarded, persisted
```

Latency budgets (measured and asserted in the benchmark script, section 15): end of speech to first audio byte of the reply under 3.0 s on a modern laptop CPU; STT of a 5 s utterance under 1.5 s; first LLM token under 1.5 s on a free API.

WebSocket protocol: JSON text frames for control (`session.start`, `turn.start`, `turn.end`, `transcript.user`, `reply.delta`, `reply.sentence`, `analysis`, `tone.report`, `xp.awarded`, `error`) and binary frames for PCM up and MP3/Opus audio down. Define the message schema once in `app/api/ws_schema.py` and generate matching TypeScript types (a small script is fine; do not add a codegen framework).

---

## 3. Tech stack (fixed, do not substitute without a DECISIONS.md entry)

**Backend:** FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLAlchemy 2, Alembic, httpx, structlog, faster-whisper, silero-vad (or webrtcvad), edge-tts, rapidocr-onnxruntime, jieba, pypinyin, praat-parselmouth, numpy, Pillow. Package/env management with `uv`.

**Frontend:** React 18, Vite, TypeScript (strict), Tailwind CSS, Zustand (small store), TanStack Query only if it removes real code (otherwise plain fetch). No component library. Icons via inline SVG or `lucide-react` (tree-shaken, only what is used).

**Data:** SQLite (single file, WAL mode). CC-CEDICT for the dictionary, an open-licensed HSK 3.0 word list with levels (for example the `complete-hsk-vocabulary` dataset on GitHub; check its licence and put attribution in README; if unavailable, build the list from CC-CEDICT plus a frequency list and record the choice). A `scripts/fetch_data.py` downloads, verifies checksums, and loads these into SQLite. Never commit the big data files.

**LLM providers (all configurable, none hardcoded):**
- Primary: Google Gemini free tier via the Gemini API (good Chinese, supports image input).
- Secondary: OpenRouter models whose ids end in `:free` (for example a Qwen or DeepSeek free model).
- Optional local: Ollama with a Qwen model, for offline use.
- Model ids live in `.env`; free-tier model names change, so verify current ones in the provider docs when writing `.env.example` and say so in a comment. Use a different (cheaper or faster) model for the analysis call than for the reply call if it helps latency.

**Not used (do not add):** LangChain/LlamaIndex, Redis, Celery, Postgres, Kubernetes, any ORM besides SQLAlchemy, any auth library, any UI kit, any analytics or tracking.

---

## 4. Repository layout

```
duihua/
  README.md  SPEC.md  DECISIONS.md  TEST_REPORT.md  HUMAN_TEST_CHECKLIST.md
  Makefile  .env.example  pyproject.toml  .pre-commit-config.yaml
  .github/workflows/ci.yml
  docs/ARCHITECTURE.md  docs/adr/0001-*.md ...
  scripts/ fetch_data.py  gen_audio_fixtures.py  bench_latency.py
  backend/
    app/
      main.py  container.py  config.py  logging.py
      api/        routers (sessions, messages, words, images, progress, debug), ws.py, ws_schema.py, schemas.py
      application/ use cases
      domain/     level.py vocabulary.py xp.py tone.py correction.py topics.py
      ports/      llm.py stt.py tts.py ocr.py scorer.py dictionary.py
      adapters/   llm/ stt/ tts/ ocr/ scoring/ dictionary/ persistence/
      resilience/ retry.py breaker.py quota.py
    migrations/
    data/topics.json  data/level_curve.json
    tests/ unit/ integration/ e2e_audio/ fixtures/
  frontend/
    src/ app/ components/ features/ (chat, voice, hover, image, tone, progress, words) lib/ styles/
    tests/ unit/  e2e/
```

---

## 5. Data model (SQLite)

- `sessions(id, mode, topic_id, level, created_at, ended_at)`
- `messages(id, session_id, role, text, pinyin_json, translation, created_at, audio_path nullable)`
- `corrections(id, message_id, original, better, reason)`
- `pronunciation_attempts(id, message_id, overall_score, syllables_json, f0_stats_json, created_at)`
- `saved_words(id, word, pinyin, definition, hsk_level, context_sentence, created_at)`
- `xp_events(id, session_id, kind, points, created_at)`
- `daily_stats(date, xp, minutes, turns)`  (streak is derived)
- `settings(key, value)`  (level, tier, show_pinyin, show_translation, speech_rate, handsfree, ...)
- `provider_usage(provider, date, requests, tokens, last_error)`
- Dictionary tables: `cedict(simplified, traditional, pinyin, definitions)` with an index on `simplified`; `hsk(word, level)`.

Use Alembic for every schema change. Indexes only where a query needs them.

---

## 6. Rich transcript and hover (frontend + backend)

- Backend `TextAnalyzer`: segments Chinese with jieba, gets pinyin per word with pypinyin (tone marks, tone sandhi enabled, heteronyms resolved by jieba context), looks up each word in `cedict`, attaches HSK level. Returns tokens: `{surface, pinyin, definitions[], hsk, chars:[{ch, pinyin, meaning}]}`. This is deterministic code, never an LLM call.
- Frontend renders with `<ruby>`. Pinyin colour-coded by tone: tone 1 red, tone 2 orange, tone 3 green, tone 4 blue, neutral grey (colour-blind safe: also vary underline style per tone; pick palette that passes contrast).
- Hover or tap a word: popover with pinyin, up to 3 definitions, HSK badge, per-character breakdown, a replay button (TTS of that word), and a Save button. Keyboard accessible (focus shows the same popover).
- Header toggles: show/hide pinyin, show/hide hanzi (listening mode), show/hide English. Per-message "play", "slow play (0.7x)", and "show translation".
- Out-of-level words in the AI's reply get a subtle dotted underline so the user knows they are above level.

---

## 7. Levels (1 to 100)

- `data/level_curve.json` defines, for each level L: vocabulary size N(L), max sentence length in characters, allowed grammar patterns, speech rate. Default N(L) grows exponentially from about 150 words at L1 to about 11,000 at L100; compute it with a formula in code and let the JSON override. Words ranked by HSK level then frequency.
- Tier picker (1 to 10) sets level to the tier's first level; a fine slider adjusts within the tier.
- **Prompt construction:** the system prompt gets the level's rules, the topic and role, and a compact allowed-vocabulary hint (not the full list; give HSK band plus a small sample, plus the user's recently saved words to reinforce).
- **Post-check (important, this is the part that makes it real engineering):** after the reply is generated, segment it and compute the share of words above the level's vocabulary cutoff (exempting proper nouns and the topic's own keywords). If above threshold (default 12 percent), regenerate once with the violating words listed as forbidden. If it still fails, accept and mark the words as out-of-level. Log the outcome. Unit-test this policy with a fake LLM.
- Suggest (never force) a level change: if the last 8 user turns averaged high quality, offer "move up?"; if they averaged low, offer "make it easier?".

---

## 8. Topics (exactly these 30, stored in `data/topics.json`)

Each has: `id`, `title_en`, `title_zh`, `ai_role`, `scenario`, `user_goal`, `keywords[]`, `min_level`.

1 Ordering at a restaurant, 2 Cafe and tea, 3 Street food and markets, 4 Grocery shopping, 5 Clothes shopping and bargaining, 6 Introducing yourself, 7 Family and relatives, 8 Friends and making plans, 9 Weather and seasons, 10 Directions and getting around, 11 Taking a taxi or ride-hailing, 12 Metro and trains, 13 Airport and flights, 14 Hotel check-in, 15 Booking a table or appointment on the phone, 16 At the doctor or pharmacy, 17 Banking and paying (WeChat Pay, Alipay), 18 Phone and internet problems, 19 Job interview, 20 Office and colleagues, 21 Studying and university life, 22 Hobbies and free time, 23 Sports and fitness, 24 Movies, music and TV, 25 Food and cooking at home, 26 Holidays and festivals (Spring Festival, Mid-Autumn), 27 Renting a home, 28 Travel plans and sightseeing, 29 News and opinions, 30 Technology and apps.

In role-play topics the AI stays in role, nudges toward the user's goal, and never breaks character except to correct. `min_level` softly warns when the chosen level is too low for the topic.

---

## 9. Pronunciation and tone scoring (`LocalToneScorer`)

Goal: honest, useful feedback on tones without paid services and without training a model. Be explicit about its limits in the UI and README.

Why not rely on STT alone: Whisper "autocorrects" mis-toned words to the likeliest valid word, which hides mistakes. So scoring works on the audio directly.

Pipeline:
1. Target text known (read-aloud mode, or the AI's last sentence being repeated) or inferred (free speech: use Whisper's transcript, flag lower confidence).
2. Convert target to syllables with tones, applying tone sandhi (3-3 becomes 2-3, 不 and 一 changes). Neutral tones are not scored.
3. Extract F0 with Parselmouth (pitch floor/ceiling set for the user's range, estimated from the utterance), convert to semitones, then normalise by the speaker's own median and spread (z-score) so it works for any voice.
4. Segment into N syllables: split voiced regions using energy valleys and F0 breaks with a small dynamic-programming alignment so the segment count equals the syllable count. If alignment confidence is low, say so instead of scoring.
5. Per syllable, compute features (start, end, mean, slope, curvature, min position) and classify against the four tone templates (T1 high level, T2 rising, T3 low dipping, T4 high falling) with a transparent, rule-based scorer. Thresholds live in `config` and are unit-tested.
6. Output per syllable: expected tone, detected tone, confidence, verdict (good, off, unclear). Overall score 0 to 100. Also compute a character-error-rate between the Whisper transcript and the target for intelligibility.
7. UI: pinyin row coloured per syllable verdict, small F0 contour sparkline (expected vs yours) on tap, plain-language tip ("tone 2 on 'ní' should rise; yours stayed flat").
8. Keep `PronunciationScorer` a Protocol so a cloud scorer can be added later. Do not implement one now.

Read-aloud mode: show a sentence (from the current topic and level), play native TTS, user records, show the report, allow retry. Store attempts.

---

## 10. Points system (pure domain code, fully unit-tested)

- +5 per user turn, +1 per 10 characters spoken (cap +10), +3 for a turn with no corrections, +2 per newly saved word, up to +10 for tone score above 70 (scaled), +15 for completing a topic goal (the AI judges and says so in the analysis JSON).
- Daily goal default 100 XP. Streak = consecutive days meeting at least 20 XP. Level progress bar from XP within the current tier.
- All values live in one `xp_rules` config object. Awards are written as `xp_events` and shown with a small, non-annoying toast.

---

## 11. UI and design

**Feel:** calm, warm, a bit bookish. A tool she wants to open every morning. Not a generic SaaS dashboard, not neon, no gradients-for-the-sake-of-gradients.

- Palette (light): paper `#F6F1E7`, ink `#1F1B16`, vermilion accent `#C8372D`, jade secondary `#3F7D6B`, muted `#8A8173`. Dark theme: warm charcoal `#1A1816` background with the same accents softened. Respect `prefers-color-scheme` and a manual toggle.
- Type: Noto Serif SC for hanzi, Inter for UI, tabular numerals for scores. Hanzi in chat bubbles at least 22 px; pinyin 0.55 of that.
- Layout (desktop): slim left rail (modes, topics, saved words, progress); centre conversation; right drawer for the word popover details, tone report and session stats. On mobile: single column, bottom bar with a large mic button.
- Mic control: one prominent circular button with a live waveform ring (canvas, cheap). States: idle, listening, thinking, speaking. Hands-free toggle. Space bar is push-to-talk on desktop.
- Micro-copy has personality and a little Chinese (加油, 再来一次, 说得不错), written like a person, not a brand. No exclamation overload, no emoji.
- Motion: only functional (message appear, popover). Respect `prefers-reduced-motion`.
- Accessibility: full keyboard path, visible focus, aria labels, contrast AA, text scales.
- Performance: JS bundle under 250 KB gzipped (check in CI), route-level code splitting only where it helps, no layout shift while streaming.

---

## 12. Engineering quality (what a reviewer at a large firm should see)

- Ruff (lint and format), mypy strict on `app/`, ESLint and Prettier, `tsc --noEmit`. Pre-commit hooks. GitHub Actions CI running lint, type-check, unit and integration tests, frontend tests, bundle-size check.
- `docs/ARCHITECTURE.md` with Mermaid diagrams: system context, component diagram, voice-turn sequence diagram, data model ER diagram. Plus a short "failure modes" table: what happens when each provider is down, rate-limited, slow.
- ADRs in `docs/adr/` (short, honest, with the alternative you rejected): local Whisper vs cloud STT; SQLite vs Postgres; rule-based tone scoring vs trained model; hexagonal layering in a one-user app (why, and what it costs); LLM fallback chain; no auth.
- `Makefile` targets: `setup`, `data`, `dev`, `test`, `lint`, `bench`, `e2e`. One command to run the app after setup: `make dev`.
- Docker: optional `Dockerfile` for the backend only; local run is the primary path because of microphone and model caches. Do not add docker-compose unless it removes real friction.
- Observability proportional to the app: structured logs, stage timings, `/readyz`, `/api/debug/timings`. No Prometheus, no tracing stack.

---

## 13. Dependency budget and anti-bloat checklist

- Backend runtime dependencies: only those named in section 3. Frontend runtime dependencies: React, React DOM, Zustand, plus at most 2 small utilities if justified in DECISIONS.md.
- Before finishing run a dead-code and unused-dependency pass (`vulture`/`ruff` on Python, `depcheck`/`knip` on the frontend) and remove everything it finds.
- No file over about 400 lines without a reason. No class where a function will do. No abstraction with a single implementation unless it is one of the ports in section 2.

---

## 14. Phases (gate each one on its tests)

**P0 Scaffold:** repo layout, config, logging, DB and migrations, `make setup/data/dev/test`, CI, health endpoints, data fetch script, empty UI shell with theme.
**P1 Text chat + rich transcript:** sessions, LLM fallback chain, reply and analysis calls, TextAnalyzer, ruby rendering, hover popover, save word, toggles, corrections card, level and topic pickers wired to prompts, level post-check.
**P2 Voice:** AudioWorklet capture, WS protocol, VAD, faster-whisper STT, sentence-chunked TTS streaming and disk cache, mic states and waveform, hands-free mode, timings.
**P3 Progress:** XP rules, daily goal, streak, level suggestions, saved words page, settings persistence.
**P4 Images:** upload and paste, validation and re-encoding, RapidOCR text extraction, vision description via Gemini, "ask me questions about this image" flow (questions in Chinese at the chosen level, answered by voice or text), tokenised OCR text with hover.
**P5 Tone scoring:** LocalToneScorer, read-aloud mode, tone report UI with contours, attempt history.
**P6 Hardening and docs:** failure injection, benchmark, bundle check, dead-code pass, README, ARCHITECTURE, ADRs, TEST_REPORT, HUMAN_TEST_CHECKLIST.

---

## 15. Tests you must write and run (and report on)

Run everything yourself. Put real results in `TEST_REPORT.md`: commands run, pass/fail counts, coverage on `domain/` and `application/` (target 85 percent or higher), benchmark numbers, and an honest "could not verify" list.

**Unit (backend):**
- Pinyin and segmentation: 你好 → nǐ hǎo (with sandhi, spoken ní hǎo noted), 银行 → yínháng (not yínxíng), 重要 → zhòngyào, 不对 → búduì, 一个 → yí gè, 一天 → yì tiān; mixed Chinese/English/digits/punctuation do not crash.
- Dictionary: lookups for common words, unknown words return empty, traditional/simplified handling.
- Level policy: N(L) monotonic, tier mapping, post-check detects out-of-level words, exempts keywords and proper nouns, regenerates once, then accepts.
- XP rules: every rule, caps, streak across day boundaries and timezones (use a fixed timezone setting), daily goal.
- Tone domain logic with **synthetic audio**: generate sine sweeps with known contours (flat, rising, dip, falling) at several pitch ranges (low male, high female); assert the classifier labels them correctly and that z-normalisation makes results voice-independent.
- Resilience: retry backoff, circuit breaker open/half-open/closed, quota tracker blocks at limit, fallback chain moves to the next provider on timeout, 429 and 5xx, and returns a clear error only when all fail.
- Upload validation: oversized, wrong type, truncated image, polyglot file, EXIF removed.

**Integration (backend, with a deterministic `FakeLLM`):**
- Full REST flows: create session, send text, receive reply and analysis, save word, progress updates.
- WebSocket voice turn using a recorded fixture WAV (generate fixtures with `scripts/gen_audio_fixtures.py` via edge-tts, committed small, or skipped with a clear marker if offline): assert transcript CER under 0.15 on clean speech, reply sentences stream in order, audio bytes arrive, XP awarded, DB rows written, per-stage timings present.
- Barge-in: user speaks while the AI is talking; playback cancels cleanly and the turn restarts without a stuck state.
- Provider outage drill: kill primary LLM mid-stream, verify failover and no duplicated sentences.
- OCR: render a PNG with Chinese text using a bundled open font (Noto Sans SC), assert extracted text matches with high similarity; also a photo-like noisy variant.
- Migrations: fresh DB and upgrade path both reach head; readiness reflects missing model or dictionary.

**Frontend:**
- Unit/component (Vitest + Testing Library): ruby rendering, tone colours, hover and keyboard popover, toggles, XP toast, mic state machine (idle, listening, thinking, speaking, error), reduced-motion.
- E2E (Playwright, Chromium with `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream --use-file-for-fake-audio-capture=fixture.wav`): complete a voice turn against a fake backend provider set; text chat with hover and save; image upload flow; level and topic change; dark mode; mobile viewport.
- Accessibility check with axe on main screens; zero serious violations.

**Performance:** `scripts/bench_latency.py` runs 20 voice turns on fixtures and prints p50 and p95 for STT, LLM first token, TTS first byte, and end-of-speech to first audio. Assert the budgets in section 2 on the fake-LLM path (to isolate local costs) and report real-provider numbers separately. Check frontend bundle size.

**Failure injection:** DB locked, disk full on audio cache, mic permission denied (UI shows clear recovery text), WebSocket drop and reconnect, TTS provider failure (falls back to text only with a visible note), malformed LLM JSON (repaired once, then degraded gracefully).

After tests pass, produce `HUMAN_TEST_CHECKLIST.md`: a short, practical list for the user to run by hand, covering things automation cannot judge: does the AI sound natural, are replies at the right level at levels 5, 30, 60 and 90, are hover meanings useful, do tone verdicts match what a native speaker would say for 10 deliberately wrong tones, is hands-free mode comfortable, does the app feel quick on her real machine, does it survive a 20 minute conversation.

---

## 16. Prompts (write these carefully, keep them short and versioned in `backend/app/prompts/`)

- **Reply prompt:** persona is a patient, curious Mandarin conversation partner. Stay at the stated level; 1 to 3 short sentences; end with a question or a natural handoff; use the topic role; do not output pinyin or English (the app adds those); never lecture mid-conversation.
- **Analysis prompt (JSON only, validated with Pydantic, one repair attempt):** given the user's last message, level and topic, return `translation_en`, `reply_translation_en`, `correction` (null if fine, else `better` and a one-line `reason` in simple English), `goal_progress` (0 to 1, and `goal_done` boolean), `suggested_words` (max 3).
- **Image prompts:** describe the image in simple Chinese at the chosen level and English; list visible text; generate 3 questions of increasing difficulty.
- Prompts are plain text templates with explicit variables, covered by snapshot tests so accidental edits show up in review.

---

## 17. Make it feel human, not machine-generated

The code should read like a good engineer wrote it over a few weeks, not like a template.

- Comments explain *why*, not *what*. Include a handful of honest notes where a real tradeoff was made ("Whisper small is the sweet spot on CPU; medium is nicer but doubles latency"). A few `TODO` notes with a concrete reason are fine; no placeholder TODOs for things that should simply be done.
- README is written in first person, in a plain voice: why this exists (a learner with no one to practise speaking with), what works well, what does not yet (known limitations section: tone scoring is rule-based and approximate, free-tier rate limits, accents), and what was learnt building it. No marketing language. Avoid words like "seamless", "robust", "powerful", "leverage", "cutting-edge", "delve".
- Commit messages are short and specific ("tone scorer: stop counting neutral syllables"), not "Implement feature X".
- Naming is plain and consistent, but do not give every function the same docstring skeleton; document only what is not obvious.
- UI copy is warm and brief. Error messages say what happened and what to do next.
- ADRs mention real doubts and what would change the decision.
- Do not pad files, add banner comments, or generate decorative diagrams that say nothing.

Human does not mean sloppy: everything still passes lint, types and tests.

---

## 18. Definition of done

- `make setup && make data && make dev` brings the app up from a clean clone; README says exactly how, including the SSH port-forward note for microphone access.
- All tests in section 15 pass, or each exception is listed in `TEST_REPORT.md` with the reason.
- Benchmarks meet budgets or the report explains why not.
- Zero paid services required; app works with only a free Gemini key (or only local Ollama).
- Lint, types, dead-code and bundle checks are clean.
- All ten features in section 1 work end to end.
- `DECISIONS.md`, `docs/ARCHITECTURE.md`, ADRs, `TEST_REPORT.md` and `HUMAN_TEST_CHECKLIST.md` exist and are accurate.

When finished, print a short summary: what was built, test results, anything that could not be verified, and the three things you would improve next.
