# 🩺 Healthcare AI Voice Agent

A full-stack healthcare voice assistant that helps users describe symptoms, performs AI-assisted triage, normalizes symptom language, maps conditions to medical specialists, and supports doctor discovery and appointment booking.

Built with **FastAPI**, **LangGraph**, **React**, **Vite**, and **PostgreSQL**.

---

## Overview

This project is designed as a conversational healthcare assistant with a voice-first interface. A user can speak symptoms, the frontend converts speech to text, and the backend processes the transcript through a structured AI workflow.

The system focuses on:

* symptom intake
* symptom normalization
* triage-oriented response generation
* specialist recommendation
* doctor lookup
* appointment booking

This is a **triage and assistance system**, not a diagnostic replacement for a medical professional.

---

## Key Features

* Voice-based symptom input using browser speech APIs
* AI-assisted symptom normalization
* LangGraph-based orchestration for structured medical conversation flow
* Specialist mapping from symptom clusters
* Doctor discovery and booking workflow
* FastAPI backend with modular service layers
* PostgreSQL-backed persistence
* Provider abstraction for LLM integrations
* React + Vite frontend for a responsive UI
* Middleware for request tracing and operational visibility

---

## Architecture

```text
User Voice Input
      ↓
React Frontend
      ↓
Speech-to-Text
      ↓
FastAPI Backend
      ↓
LangGraph Workflow
      ↓
Symptom Normalization
      ↓
Triage / Risk Assessment
      ↓
Specialist Mapping
      ↓
Doctor Lookup
      ↓
Appointment Booking
      ↓
PostgreSQL
```

---

## Repository Structure

```text
Healthcare-AI-Voice-agent/
├── backend/
│   ├── api/
│   ├── providers/
│   ├── repositories/
│   ├── services/
│   ├── prompts/
│   ├── chat_agent.py
│   ├── langgraph_llm_agents.py
│   ├── db.py
│   ├── config.py
│   ├── models.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

## Tech Stack

### Backend

* FastAPI
* Python
* LangGraph
* PostgreSQL
* Uvicorn

### Frontend

* React
* Vite
* JavaScript
* CSS

### AI / Workflow

* LLM provider abstraction
* LangGraph orchestration
* Prompt-driven symptom analysis

---

## Backend Design

The backend is organized into layers:

### `api/`

HTTP route handlers and API entry points.

### `services/`

Business logic and orchestration.

### `repositories/`

Database access and query abstraction.

### `providers/`

LLM provider implementations.

### `prompts/`

Prompt templates used by the agent workflow.

### Core modules

* `main.py` — FastAPI application entry point
* `langgraph_llm_agents.py` — LangGraph workflow and agent coordination
* `chat_agent.py` — conversational agent logic
* `db.py` — database connection handling
* `config.py` — environment and application configuration
* `models.py` — data schemas and domain models

---

## Frontend Design

The frontend provides the user-facing voice interaction layer.

It includes:

* voice capture
* transcript display
* chat-style responses
* specialist / recommendation display
* appointment-related UI flows

The frontend is built with **React + Vite** for fast development and a lightweight build pipeline.

---

## Getting Started

### Prerequisites

* Python 3.12+
* Node.js 18+
* PostgreSQL
* Git

---

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in `backend/`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthcare
DB_USER=your_user
DB_PASSWORD=your_password

FRONTEND_ORIGIN=http://localhost:5173

OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
```

### Run Backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will typically run at:

```text
http://localhost:5173
```

---

## Database Setup

Set up PostgreSQL and create the required schema before running the application.

Example:

```bash
psql -U postgres
```

```sql
CREATE DATABASE healthcare;
CREATE USER healthcare_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE healthcare TO healthcare_user;
```

Then apply your schema and stored procedures if your current build uses them.

---

## Typical Flow

1. User speaks symptoms into the frontend
2. Speech is converted to text
3. Transcript is sent to FastAPI
4. LangGraph processes the input
5. Symptoms are normalized
6. Triage logic determines urgency and context
7. Relevant specialist types are returned
8. Doctor results are fetched
9. Appointment flow continues if needed

---

## API Endpoints

The exact routes may vary depending on your implementation, but the backend is structured around endpoints such as:

* `POST /chat`
* `POST /run_langgraph`
* authentication-related routes
* doctor lookup routes
* appointment-related routes

---

## Development Notes

This project follows a modular backend architecture to keep AI orchestration, database access, and business logic separated.

That makes it easier to:

* swap LLM providers
* extend the triage workflow
* test individual components
* maintain clean database access
* evolve the UI independently

---

## Important Note

This application is intended to assist with symptom intake and triage-style guidance.

It should not be treated as a substitute for:

* a licensed doctor
* emergency services
* formal diagnosis
* medical treatment decisions

---

## Future Improvements

* multi-language support
* stronger emergency red-flag detection
* better symptom extraction
* appointment reminders
* authentication and user profiles
* medical record integration
* improved voice UX
* mobile app support
# Healthcare AI Voice Agent - Update
