from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from fastapi import Header, HTTPException
from auth.supabase_client import supabase
from fastapi import Depends

router = APIRouter(tags=["Auth"])

def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    print("AUTH HEADER:", authorization)

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "", 1)

    try:
        user = supabase.auth.get_user(token)
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

from fastapi import HTTPException

@router.post("/auth/signup")
def signup(payload: SignUpRequest):
    # 1. Signup user
    try:
        auth_response = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if auth_response.user is None:
        raise HTTPException(status_code=400, detail="Signup failed")

    user = auth_response.user

    # 2. Create profile
    try:
        supabase.table("profiles").insert({
            "id": user.id,
            "name": payload.name,
            "avatar_url": None
        }).execute()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"User created but profile creation failed: {str(e)}"
        )

    return {
        "user_id": user.id,
        "email": user.email,
        "name": payload.name
    }


from fastapi import HTTPException
from supabase_auth.errors import AuthApiError

@router.post("/auth/login")
def login(payload: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
    except AuthApiError as e:
        raise HTTPException(
            status_code=401,
            detail=e.message
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal authentication error"
        )

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "user": {
            "id": response.user.id,
            "email": response.user.email
        }
    }


@router.get("/auth/me")
def get_me(user=Depends(get_current_user)):
    profile = (
        supabase
        .table("profiles")
        .select("name, avatar_url")
        .eq("id", user.id)
        .single()
        .execute()
    )

    return {
        "id": user.id,
        "email": user.email,
        "name": profile.data.get("name"),
        "avatar_url": profile.data.get("avatar_url")
    }

from pydantic import BaseModel

class RefreshRequest(BaseModel):
    refresh_token: str

from fastapi import HTTPException

@router.post("/auth/refresh")
def refresh_token(payload: RefreshRequest):
    try:
        response = supabase.auth.refresh_session(payload.refresh_token)

        if response.session is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
