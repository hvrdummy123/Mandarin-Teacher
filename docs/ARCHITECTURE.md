# System architecture & design

How duihua is put together, **why** this shape, what problem it solves, where it wins, and how to improve it.

---

## 1. The problem this design solves

Most Mandarin study tools optimise for **reading and drills**. The gap for a solo learner is:

| Pain | What we need |
| --- | --- |
| Nowhere to *speak* daily | Low-friction voice conversation with an AI that stays in Mandarin |
| Transcripts that are hanzi-only | Stacked **pinyin · hanzi · English** so intermediate learners can follow |
| Opaque word meanings | Instant lookup + save without leaving the chat |
| Cloud apps that need accounts / paid tiers | Single-user, local-first, free-tier or local models |
| One flaky API killing the session | Swappable LLM/STT/TTS with failover when free tiers 429 |
| Slow “chatbot wrapped in a UI” | A measured voice hot path (STT → reply → TTS) with parallel analysis |

So the architecture is not “a chatbot with a mic.” It is a **speaking coach pipeline**: capture speech, understand it in context, reply and speak back, enrich the transcript locally, and keep every vendor behind a replaceable adapter.

---

## 2. High-level architecture

Hexagonal (**ports & adapters**). The domain never imports Gemini, Whisper, or Edge TTS. The UI talks to a thin API; use cases orchestrate ports; adapters implement them.

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React / Vite / Zustand)                           │
│  Chat · Topics · Words · Progress                           │
│  Mic → AudioWorklet · Browser STT (live) · TTS playback     │
└───────────────┬─────────────────────────────┬───────────────┘
                │ REST (JSON)                 │ WebSocket
                │ sessions, enrich, words…    │ PCM up · events + audio down
                ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI  ·  api/ (routers, schemas, ws)                    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  application/   voice turn · chat · enrich · transcript     │
│                 repair · text analysis                      │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  domain/        level · topics · correction · vocabulary    │
│  (pure Python — no HTTP, no SDKs)                           │
└────────────────────────────┬────────────────────────────────┘
                             │ ports (Protocols)
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   LLM adapters         STT / TTS            Dictionary / DB
   Gemini               Whisper              Cedict SQLite
   OpenRouter (+chain)  Edge TTS (+cache)    duihua.db (sessions)
   Ollama               Frame VAD
```

**Dependency rule:** arrows point inward. `domain` → nothing outside itself. `application` → domain + ports. `adapters` implement ports. `api` and `container.py` wire everything once.

---

## 3. Why this design (not a monolith or a mega-framework)

### 3.1 Hexagonal / ports & adapters

| Chosen | Rejected | Why |
| --- | --- | --- |
| Explicit `Protocol` ports + adapters | LangChain / LlamaIndex agent graphs | Free-tier Chinese coaching needs **control** over prompts, latency, and failover — not a framework’s agent loop |
| One composition root (`container.py`) | Full DI container | One user, one process; a 50-line wire-up beats magic |
| Domain pure Python | Business logic in route handlers | Level rules, topics, corrections stay testable without network |

**Advantage:** swap OpenRouter → Ollama, or Whisper → another STT, by changing `.env` and an adapter — not rewriting chat.

### 3.2 Local-first single process

| Chosen | Rejected | Why |
| --- | --- | --- |
| SQLite (WAL) + two DB files | Postgres / Redis / Celery | Solo learner; no multi-tenant scale problem; fewer moving parts |
| App DB ≠ dictionary DB | One giant DB | `make data` can rebuild the lexicon without wiping sessions |
| Bind `127.0.0.1` | Public SaaS deploy | Mic requires localhost/HTTPS; privacy matches “practice on my laptop” |

**Advantage:** clone → `make setup` → `make dev` with no cluster.

### 3.3 LLM FallbackChain + resilience

Free Gemini/OpenRouter keys **will** 429. The design assumes that:

```
complete(prompt)
  → try providers in LLM_PROVIDERS order
  → timeout / 429 / 5xx → next provider (and next :free model id)
  → circuit breaker opens after repeated failure
  → if *all* open, force a half-open probe (never soft-lock forever)
  → never invent a fake “offline AI” reply
```

**Advantage:** the product degrades to “retry in a minute” with the learner’s line kept — not a hallucinated coach. Paid OpenRouter or local Ollama plugs in without UI changes.

### 3.4 Split speech path (browser STT + Whisper)

```
While speaking:  Browser SpeechRecognition (zh-CN) → live bubble
                 POST /api/enrich → pinyin / rough English / topic repair
After turn:      Prefer browser transcript as heard_hint (skip Whisper when good)
                 else faster-whisper (base, MPS on Apple Silicon)
                 → optional topic-aware transcript_repair
                 → LLM reply + analysis (parallel) → Edge TTS (cached)
```

**Advantage:** perceived latency drops (captions while speaking); Whisper stays the accuracy safety net; topic repair fixes common near-homophones (e.g. 借口 → 家) without “training” the browser LM.

### 3.5 Local linguistic enrichment (not the LLM)

Pinyin, segmentation (jieba), dictionary senses, and HSK tags come from **CC-CEDICT + local code** (`TextAnalyzer`), not from asking the model to annotate every character.

**Advantage:** deterministic, free, fast; LLM budget goes to *conversation* and *corrections*.

### 3.6 Frontend: thin SPA + Zustand

Four screens, English-first chrome, mic-primary chat. No UI kit, no TanStack Query in the core path — plain `fetch` / WebSocket and a small Zustand store.

**Advantage:** UI stays understandable for a portfolio/personal project; product feel comes from transcript UX, not dashboard chrome.

---

## 4. Runtime flows that matter

### 4.1 Voice turn (hot path)

```
Mic (tap toggle)
  → 16 kHz PCM over WebSocket
  → VAD only in hands-free mode (tap mode: user ends the turn)
  → STT (hint or Whisper) → repair(topic)
  → persist user message early (release SQLite before network waits)
  → parallel:
       A) LLM reply → sentence-split → TTS → audio to client
       B) LLM analysis JSON → translation / correction card
  → enrich tokens for both sides → XP stub
```

Design pressure: **time-to-first-audio**. Analysis and TTS overlap; topic openings are canned JSON (no LLM) so role-play starts instantly.

### 4.2 Review-before-send

Optional UX gate: speak → show repaired transcript (pinyin/hanzi/English) → **Send** or **Discard**. Same enrich/repair pipeline; prevents bad STT from burning an LLM call and confusing the dialogue.

### 4.3 Data stores

| Store | Role |
| --- | --- |
| `data/duihua.db` | Sessions, messages, saved words, usage, settings |
| `data/dictionary.db` | CEDICT + HSK (rebuildable) |
| `data/tts_cache/` | Edge TTS audio by text hash |
| `data/audio/{session}/` | Saved WAVs for future tone scoring |

---

## 5. Where this design is advantageous

1. **Vendor independence** — Gemini today, Ollama tonight; ports keep the product stable.
2. **Honest free-tier operation** — breakers, multi-model lists, no fake replies.
3. **Learner-visible latency** — live captions + parallel TTS/analysis beat a single blocking “think” spinner.
4. **Testability** — domain and repair logic unit-test without keys; adapters can be faked.
5. **Portfolio clarity** — architecture matches the README story: speaking coach, not a wrapper around one SaaS SDK.
6. **Safe defaults** — localhost bind, CORS locked to Vite, upload/audio caps, secrets only in `.env`.

---

## 6. Trade-offs (accepted)

| Trade-off | Cost | Why we accept it |
| --- | --- | --- |
| SQLite single writer | Occasional lock under load | Mitigated with `busy_timeout` + early commit; one user |
| Free LLM quality/limits | 429s, uneven Chinese | Documented; Ollama/paid OpenRouter escape hatches |
| Browser STT variance | Mishears | Review-before-send + topic repair + Whisper fallback |
| No multi-user / auth | Can’t “ship as a SaaS” as-is | Out of product scope by design |
| Hand-rolled breaker/retry | Not battle-tested infra | ~60 lines, no new dependency, enough for laptop use |

---

## 7. How we can improve

Ordered by leverage for the speaking-coach goal:

### Near term
- **Streaming LLM tokens over the WebSocket** end-to-end (partially chunked today) for snappier first sentence
- **Richer topic lexicons** for transcript repair (more scenarios, measured false-positive rate)
- **Stronger OpenRouter model lists** / optional paid defaults documented for demos
- **Progress & XP** fully wired (rules exist in domain; UI still light)

### Medium term (spec phases)
- **Pronunciation / tone scoring** on saved WAVs (Parselmouth / local scorer port already reserved)
- **Image practice** (OCR + vision adapter) for real-world Chinese text
- **Read-aloud mode** for tone drills
- **PWA install** + offline dictionary shell

### Structural (if the project grows)
- Extract voice pipeline metrics into a small dashboard (timings already at `/api/debug/timings`)
- Optional Postgres only if you ever leave single-user
- Cloud STT adapter behind the same `STTProvider` port if Whisper-on-CPU becomes the bottleneck on low-end machines
- Real SSE for analysis patches if WebSocket event surface gets crowded

### What *not* to “improve” without a product reason
- Adding LangChain, Redis, Kubernetes, or an auth stack — they solve problems this design deliberately does not have
- Replacing local CEDICT enrichment with LLM annotations — cost and inconsistency for little gain

---

## 8. Map to code

| Concern | Location |
| --- | --- |
| Wiring | `backend/app/container.py`, `config.py` |
| Ports | `backend/app/ports/` |
| Voice use case | `backend/app/application/voice_turn.py` |
| Chat / enrich | `backend/app/application/chat.py`, `text_analyzer.py`, `transcript_repair.py` |
| LLM failover | `backend/app/adapters/llm/fallback.py` |
| Resilience | `backend/app/resilience/` |
| WS protocol | `backend/app/api/ws.py`, `ws_schema.py` |
| UI shell / chat | `frontend/src/components/Shell.tsx`, `features/chat/`, `features/voice/` |
| Product source of truth | `SPEC.md` |
| Small choice log | `DECISIONS.md` |

---

## 9. One-sentence summary

**duihua is a local hexagonal speaking-coach: a React client drives a FastAPI voice pipeline whose domain stays pure, while LLM/STT/TTS sit behind failover adapters so a solo Mandarin learner can practise every day without betting on a single free API.**
