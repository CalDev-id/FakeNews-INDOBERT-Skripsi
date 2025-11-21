import os
import gspread
import pandas as pd
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory

from agents.predict.predict import classify_berita
from agents.get_evidence.google_search import google_search
from agents.get_evidence.scrape_html import scrape_html
from agents.explanation.explanation import explanation

import os
import json
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

# === TOOLS ===
def classify_berita_tool(input_str: str):
    """
    input_str format:
    {"title": "...", "content": "..."}
    """
    try:
        data = json.loads(input_str)
        title = data.get("title", "")
        content = data.get("content", "")
    except:
        # fallback untuk format "title=..., content=..."
        parts = [p.strip() for p in input_str.split(",")]
        title = parts[0].split("=",1)[1].strip()
        content = parts[1].split("=",1)[1].strip()

    return classify_berita(title, content)


def get_evidence_tool(input_str: str) -> str:
    try:
        data = json.loads(input_str)
        title = data.get("title", "")
    except:
        # fallback untuk format "title=..., content=..."
        parts = [p.strip() for p in input_str.split(",")]
        title = parts[0].split("=",1)[1].strip()

    total_results: int = 10
    scrape_limit: int = 1
    query = title

    # 1. Google Search
    links = google_search(query, total_results=total_results)

    # 2. ScrapingBee
    scraped = []
    for url in links[:scrape_limit]:
        content = scrape_html(url)
        if content:
            scraped.append(content)

    return {
        "links": links,
        "evidence": scraped
    }
def classifiy_berita_with_evidence_tool(input_str: str) -> str:
    try:
        data = json.loads(input_str)
        title = data.get("title", "")
        content = data.get("content", "")
    except:
        # fallback untuk format "title=..., content=..."
        parts = [p.strip() for p in input_str.split(",")]
        title = parts[0].split("=",1)[1].strip()
        content = parts[1].split("=",1)[1].strip()

    classification = classify_berita(title, content)

    total_results = 10
    scrape_limit = 3
    links = google_search(title, total_results=total_results)

    scraped = []
    for url in links[:scrape_limit]:
        content = scrape_html(url)
        if content:
            scraped.append({
                "url": url,
                "content": content
            })

    return {
        "input_user": input_str,
        "classification": classification,
        "evidence_scraped": scraped,
    }

# === Initialize LLM ===
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
)

# === Register tools ===
tools = [
    Tool.from_function(func=classify_berita_tool, name="classify_berita_tanpa_bukti", description="Klasifikasikan berita tanpa bukti. Input format: 'title=Judul berita, content=Isi berita'"),
    Tool.from_function(func=get_evidence_tool, name="get_evidence", description="Dapatkan bukti dari judul berita yang diberikan, berikan link link dari hasil pencarian Google, dan bukti yang di-scrape dari link tersebut. Input format: 'title=Judul berita'"),
    Tool.from_function(func=classifiy_berita_with_evidence_tool, name="classify_berita_with_evidence", description="Prediksi klasifikasi berita dengan pencarian bukti Input format: 'title=Judul berita, content=Isi berita'"),

]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
    agent_kwargs={
        "system_message": SystemMessage(
            content=(
                "Kamu adalah asisten AI yang membantu mengklasifikasikan berita sebagai hoaks atau valid. "
                "Bantulah pengguna dengan memberikan informasi yang akurat dan relevan berdasarkan klasifikasi berita dan bukti yang ditemukan. "
            )
        )
    }
)