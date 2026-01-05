import json
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from agents.predict.predict import classify_berita
from agents.predict.predict import advance_classify_berita
from agents.get_evidence.google_search import google_search
from agents.get_evidence.scrape_html import scrape_html
from agents.explanation.explanation import explanation
from agents.claim_check.claim_check import claim_check
from agents.chat.chat import agent
from auth.supabase_client import supabase
from typing import List, Any, Optional
import asyncio
from routers import predict, chat, news, auth, profile


#uvicorn main:app --reload
#uvicorn main:app --host 0.0.0.0 --port 8000
#hcsp_1_5g
#http://192.168.50.110:8000/docs

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "Fake News Detection API"}

app.include_router(predict.router)
app.include_router(chat.router)
app.include_router(news.router)
app.include_router(auth.router)
app.include_router(profile.router)




