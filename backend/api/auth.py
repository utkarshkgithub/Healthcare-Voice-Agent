"""
Auth API routes — /auth/login, /auth/register, /auth/me

All patient-scoped routes take their identity from the bearer token rather
than from a path parameter, so one patient cannot read another's records by
changing a URL.
"""
import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth import create_access_token, get_current_user
from models import LoginRequest
from repositories import auth_repository, patient_repository

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


@router.post("/login")
def login(request: LoginRequest):
    logger.info(f"[auth] Login attempt for {request.email}")
    try:
        user_id = auth_repository.login_user(request.email, request.password)
    except Exception as e:
        logger.error(f"[auth] DB error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_info = auth_repository.get_user_info(user_id)
    return JSONResponse(
        content={
            "message": "Login successful",
            "access_token": create_access_token(user_id),
            "token_type": "bearer",
            "user_id": user_id,
            "name": user_info["name"] if user_info else "Patient User",
            "email": request.email,
            "patient_id": patient_repository.get_patient_id_by_user(user_id),
        }
    )


@router.post("/register", status_code=201)
def register(request: RegisterRequest):
    logger.info(f"[auth] Registration attempt for {request.email}")
    try:
        user_id = auth_repository.register_user(
            request.name, request.email, request.password
        )
    except psycopg.errors.UniqueViolation:
        # Registration of an existing address is a client error, not a 500.
        raise HTTPException(status_code=409, detail="Email already registered.")
    except Exception as e:
        logger.error(f"[auth] DB error during registration: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

    if not user_id:
        raise HTTPException(status_code=400, detail="Registration failed")

    return {
        "message": "Registration successful",
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
        "user_id": user_id,
        "name": request.name,
        "email": request.email,
        "patient_id": patient_repository.get_patient_id_by_user(user_id),
    }


@router.get("/me")
def get_me(user_id: int = Depends(get_current_user)):
    """Returns the authenticated user. The id comes from the token, not the URL."""
    user_info = auth_repository.get_user_info(user_id)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        **user_info,
        "user_id": user_id,
        "patient_id": patient_repository.get_patient_id_by_user(user_id),
    }