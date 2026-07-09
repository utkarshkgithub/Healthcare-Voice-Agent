"""
FastAPI application entry point.

Responsibilities (only):
  - App initialization
  - CORS middleware
  - Request ID middleware
  - Global exception handler
  - Router registration

No SQL. No business logic.
"""
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import Config

# Routers
from api.auth import router as auth_router
from api.patients import router as patients_router
from api.appointments import router as appointments_router
from api.triage import router as triage_router
from api.chat import router as chat_router
from api.payments import router as payments_router
from api.voice import router as voice_router

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ─── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Healthcare AI Voice Agent API",
    version="1.0.0",
    description="AI-powered voice triage and appointment booking API.",
)

# ─── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[Config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request ID middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ─── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )

# ─── Routers ───────────────────────────────────────────────────────────────────
# Keep backward-compatible flat paths (frontend calls /login, not /auth/login)
app.include_router(auth_router, prefix="")   # /login
app.include_router(patients_router)           # /patient-details, /medical-history
app.include_router(appointments_router)       # /appointments
app.include_router(triage_router)             # /run_langgraph
app.include_router(chat_router)              # /chat — secure LLM proxy
app.include_router(payments_router)          # /payments
app.include_router(voice_router)             # /stt, /tts — voice provider endpoints

# ─── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Healthcare AI Voice Agent API is running."}