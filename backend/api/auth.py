"""
Auth API routes — /auth/login, /auth/register
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from models import LoginRequest
from repositories import auth_repository
import logging

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


@router.post("/login")
def login(request: LoginRequest):
    logger.info(f"[auth] Login attempt: {request.email}")
    try:
        user_id = auth_repository.login_user(request.email, request.password)
    except Exception as e:
        logger.error(f"[auth] DB error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

    if user_id:
        return JSONResponse(content={"message": "Login successful", "user_id": user_id})
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/register")
def register(request: RegisterRequest):
    logger.info(f"[auth] Registration attempt: {request.email}")
    try:
        user_id = auth_repository.register_user(
            request.name, request.email, request.password
        )
    except Exception as e:
        logger.error(f"[auth] DB error during registration: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

    if user_id:
        return JSONResponse(
            status_code=201,
            content={"message": "Registration successful", "user_id": user_id},
        )
    raise HTTPException(status_code=400, detail="Registration failed")
