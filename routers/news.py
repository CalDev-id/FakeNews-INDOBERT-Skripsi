from fastapi import APIRouter, Depends
from pydantic import BaseModel
import os
from auth.supabase_client import supabase
from fastapi import HTTPException
from uuid import UUID
from routers.auth import get_current_user
from typing import List, Optional

router = APIRouter(tags=["News"])

class Classification(BaseModel):
    final_label: str
    final_confidence: float

class NewsPayload(BaseModel):
    url: str
    title: str
    content: str
    classification: Classification
    evidence_links: Optional[List[str]] = None
    evidence_scraped: Optional[list] = None
    explanation: Optional[str] = None

@router.get("/news")
def get_news():
    result = supabase.table("news").select("*").execute()
    return result.data

@router.get("/news/hoaks")
def get_hoax_news():
    result = (
        supabase
        .table("news")
        .select("*")
        .eq("classification->>final_label", "hoaks")
        .execute()
    )
    return result.data


@router.get("/news/valid")
def get_valid_news():
    result = (
        supabase
        .table("news")
        .select("*")
        .eq("classification->>final_label", "valid")
        .execute()
    )
    return result.data

@router.get("/news/id/{news_id}")
def get_news_by_id(news_id: UUID):
    result = (
        supabase
        .table("news")
        .select(
            """
            *,
            author:profiles (
                id,
                name,
                avatar_url
            )
            """
        )
        .eq("id", str(news_id))
        .single()
        .execute()
    )

    return result.data


@router.get("/news/search")
def search_news(q: str):
    result = supabase.table("news").select("*").ilike("title", f"%{q}%").execute()
    return result.data

@router.post("/news")
def insert_news(
    payload: NewsPayload,
    user=Depends(get_current_user)   # 🔥 ambil user login
):
    user_id = user.id                # 🔥 auth.uid()

    data = payload.dict()
    data["author_id"] = user_id      # 🔥 SET DI SINI

    result = (
        supabase
        .table("news")
        .insert(data)
        .execute()
    )

    return result.data

@router.get("/news/my")
def get_my_news(user=Depends(get_current_user)):
    return (
        supabase
        .table("news")
        .select("*")
        .eq("author_id", user.id)
        .order("inserted_at", desc=True)
        .execute()
        .data
    )
