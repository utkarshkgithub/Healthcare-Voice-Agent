# 🩺 Healthcare AI Voice Agent

A voice-first triage assistant. A patient describes their symptoms by speaking;
the system extracts them, screens for emergencies, assesses risk, predicts a likely
condition, gives guidance, and maps the symptoms to real specialists with bookable
slots in PostgreSQL.

The clinical decisions are not made by a language model. A deterministic rules layer
decides escalation, and the model can only ever escalate further — never talk the
system out of an emergency.

**This is a triage and routing system. It does not diagnose.**

---

## Why the LLM is not the decision maker

An LLM wrapper asks a model what to do. This system constrains it:

| Concern | Who decides |
|---|---|
| Is this an emergency? | `red_flags.py` rules **OR** the model — the model may only escalate |
| What urgency? | Model's `Urgency` value, parsed and used to **route the graph** |
| Which specialties? | Database mapping via `sp_get_specialists`, LLM may only pick from that list |
| Which doctors/slots? | PostgreSQL, with a unique constraint preventing double-booking |
| Was money taken? | The database, re-checked at booking time |

Measured on a 27-case golden set (`backend/evals/`):

```
accuracy               100.0%
false-negative rate      0.0%   <- emergencies missed
false-positive rate      0.0%
```

```bash
cd backend && python -m evals.run_eval --offline   # no network, no API cost
```

---

## Architecture

```
Browser (React 19 + Vite)
  VoiceAgent.tsx
    ├── utils/voiceProvider.ts    STT/TTS adapter (interface + 2 implementations)
    └── utils/api.ts              typed HTTP client
          │
          ▼
FastAPI  (main.py — middleware, CORS, request IDs, routers)
  │
  ├── /chat          → chat_agent.build_chat_graph()      8 nodes, 2 routers
  ├── /run_langgraph → triage_service.run_triage()        4 nodes, linear
  ├── /auth /patient-details /medical-history /appointments
  ├── /payments/{create-order,verify,webhook}
  └── /stt /tts      → voice/factory.py
          │
   ┌──────┴─────────┐
 llm/              repositories/          voice/
 OpenAI|Cerebras   → psycopg pool → PG    Deepgram | WebApi (browser)
 Gemini
 prompts/*.md  (9 templates)
```

**Layer rule:** routes handle HTTP only; `services/` owns business logic;
`repositories/` owns data access and contains no business logic. No route contains
SQL and no node imports a vendor SDK.

---

## The conversational pipeline — 8 nodes

`backend/chat_agent.py`

```
extract_symptoms
      │
      ▼
check_emergency ──── emergency? ──▶ emergency_response ──▶ END   (no LLM on this path)
      │ no
      ▼
check_missing_info ── missing info & rounds < cap? ──▶ ask_questions ──▶ END
      │ no
      ▼
risk_assessment ── Urgency: Emergency? ──▶ emergency_response ──▶ END
      │ no
      ▼
generate_prediction
      │
      ▼
provide_guidance ──▶ END
```

Three details that matter:

- **The emergency path calls no model.** A deterministic rules layer runs first; if
  it fires, the graph short-circuits to a hard-coded instruction to seek care.
- **The clarifying-question cap is server-enforced.** `MAX_CLARIFYING_QUESTIONS`
  lives in the graph, and the client-supplied counter is clamped, so a safety bound
  is never client-controlled.
- **Urgency changes control flow.** `Urgency: Emergency` routes to the hard stop;
  `Urgent` prevents the guidance prompt from recommending self-care.

## The triage pipeline — 4 nodes

`backend/langgraph_llm_agents.py`

```
normalize_symptoms → specialist_lookup → recommend_specialists → fetch_doctors → END
```

Only the LLM may pick from the specialties the database returned; a hallucinated
name is filtered out on the way back.

---

## Provider abstraction

Both the LLM and speech layers sit behind an interface, so nothing outside those
files imports a vendor SDK.

**LLM** — `llm/base.py` (ABC) + `llm/factory.py`, selected by `LLM_PROVIDER`:

- `openai` (default) — `langchain_openai`, `gpt-4.1-mini`
- `cerebras` — OpenAI-compatible endpoint, `qwen-3.8-27b`. Recommended for this
  app: the pipeline makes up to five sequential calls per turn, so cost and latency
  dominate. Reuses the installed SDK, so there is no second dependency.
- `gemini` — `google-generativeai`, `gemini-2.5-flash`

Adding a fourth OpenAI-compatible vendor is a class with four attributes and one
line in the factory.

**Voice** — `voice/base.py` + factory, selected by `VOICE_PROVIDER`:

- `webapi` (default) — browser `SpeechRecognition` / `speechSynthesis`. Free, no
  API key. Server endpoints return **501** by design, which makes the delegation
  explicit rather than a silent failure.
- `deepgram` — server-side STT (`nova-2`) and TTS (`aura-asteria-en`)

The frontend mirrors this in `utils/voiceProvider.ts` with a
`VoiceProviderAdapter` interface and two implementations.

---

## Prompts

Nine templates in `backend/prompts/`, loaded by name from disk so they can be
reviewed in a diff and edited without a deploy.

| Prompt | Purpose |
|---|---|
| `chat_extract_symptoms` | utterance → symptom list |
| `chat_check_emergency` | emergency screen (second gate) |
| `chat_check_missing_info` | which critical field is missing |
| `chat_ask_questions` | phrase one clarifying question |
| `chat_risk_assessment` | urgency + confidence |
| `chat_prediction` | structured JSON prediction |
| `chat_guidance` | patient-facing guidance |
| `normalize` | colloquial → clinical terms |
| `recommend` | pick specialists from the allowed list |

---

## API

Thirteen endpoints. The care journey is six of them:

| # | Endpoint | Auth | Role |
|---|---|---|---|
| 1 | `POST /chat` | – | conversational triage |
| 2 | `POST /run_langgraph` | – | **specialist mapping + doctor discovery** |
| 3 | `GET /patient-details` | ✅ | discovery context |
| 4 | `POST /appointments` | ✅ | **booking** |
| 5 | `POST /payments/create-order` | ✅ | **booking** |
| 6 | `POST /payments/verify` | ✅ | **booking** |

Supporting: `POST /auth/login`, `POST /auth/register`, `GET /auth/me`,
`GET /medical-history`, `POST /payments/webhook`, `POST /stt`, `POST /tts`.

`/patient-details` and `/medical-history` take **no** `user_id` parameter —
identity comes from the bearer token.

---

## Security

- **bcrypt** password hashing via `pgcrypto`; plaintext is never stored.
- **Signed JWTs** (HS256) using stdlib `hmac`/`hashlib`, with constant-time
  comparison and one opaque 401 for every failure mode.
- `JWT_SECRET` is **required at startup** — there is no insecure default.
- **Payment before booking.** An order's amount is fixed server-side when created,
  and `/appointments` re-checks that the payment was captured by us. A forged or
  omitted `payment_id` returns **402**.
- **No double-booking.** A unique constraint plus a conditional `UPDATE` inside
  `sp_create_appointment`; a slot taken concurrently returns **409**.
- Every response carries an `X-Request-ID`; internal errors never leak a traceback.

### Known gaps

- **Not for clinical use.** The red-flag pattern list needs clinical sign-off, and
  the golden set is small.
- **PHI in logs and with the LLM vendor.** Symptom text is logged at INFO and sent
  to the configured provider. Production needs redaction, a BAA and explicit
  consent.
- **No rate limiting** on `/chat`, which is an authenticated LLM proxy.
- **JWTs cannot be revoked** before expiry; a refresh token or denylist is needed.
- **Appointment booking has no idempotency key**, so a retried request can create a
  duplicate appointment.

---

## Setup

### Prerequisites

Python 3.12+, Node 18+, PostgreSQL 14+.

### Database

```bash
psql "$DATABASE_URL" -f backend/schema.sql
```

Idempotent — safe to re-run. Creates the tables, all stored procedures, and seeds
7 specialties, 93 symptom→specialty mappings, 20 doctors and 14 days of slots.

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill it in
uvicorn main:app --reload
```

`.env` must set `DATABASE_URL`, `JWT_SECRET` and the key for your chosen
`LLM_PROVIDER`. Startup fails with an actionable message if any are missing.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # generate a JWT_SECRET
```

### Frontend

```bash
cd frontend
npm install
echo 'VITE_API_BASE_URL=http://localhost:8000' > .env
npm run dev
```

---

## Tests

```bash
cd backend
python -m pytest tests -q
```

46 tests covering prompt rendering, the red-flag layer, the graph routers, and the API surface
against a real database. The API tests stub the LLM where a model would otherwise
be needed — which is what the provider abstraction is for.

```bash
python -m evals.run_eval --offline        # golden set, deterministic layer only
python -m evals.run_eval --fail-under 0.0 # CI gate on false-negative rate
```

```bash
cd frontend && npm run build:check         # tsc --noEmit && vite build
```

---

## Project layout

```
backend/
├── main.py               app, CORS, request-ID middleware, global error handler
├── config.py             all env config + startup validation
├── db.py                 bounded psycopg connection pool
├── schema.sql            tables, stored procedures, seed data
├── auth.py               JWT issue/verify (stdlib only)
├── red_flags.py          deterministic emergency rules
├── chat_agent.py         conversational graph (8 nodes)
├── langgraph_llm_agents.py  triage graph (4 nodes)
├── models.py             request/response schemas
├── api/                  7 routers, HTTP only
├── services/             triage_service
├── repositories/         data access, stored procedures only
├── llm/                  base, factory, openai_compatible, 3 providers, prompts loader
├── voice/                base, factory, deepgram, webapi
├── prompts/              9 templates
├── evals/                golden_cases, run_eval
└── tests/                red flags, routers, API integration

frontend/src/
├── pages/                Login, Signup, Dashboard, VoiceAgent
├── components/VoiceAgent/ VoiceOrb, MessageList, ChatInput, DoctorList
└── utils/                api.ts (typed client), voiceProvider.ts (adapter)
```