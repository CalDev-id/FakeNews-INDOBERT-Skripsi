import os
from turtle import title
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
def get_news_tool(url: str) -> str:
    scraped_main = scrape_html(url)
    if not scraped_main or scraped_main.get("content") == "Tidak berhasil ekstrak isi artikel":
        return {
            "error": "Gagal mengambil artikel dari URL",
            "url": url
        }

    title = scraped_main.get("judul", "")
    content = scraped_main.get("content", "")
    return json.dumps({
        "title": title,
        "content": content
    }, ensure_ascii=False)

def classify_news_without_evidence_tool(input_str: str):
    try:
        data = json.loads(input_str)
        title = data.get("title", "")
        content = data.get("content", "")
    except:
        # fallback untuk format "title=..., content=..."
        parts = [p.strip() for p in input_str.split(",")]
        title = parts[0].split("=",1)[1].strip()
        content = parts[1].split("=",1)[1].strip()
    hasil = classify_berita(title, content)
    return json.dumps((hasil), ensure_ascii=False)


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

    return json.dumps({
        "links": links,
        "evidence": scraped
    }, ensure_ascii=False)

def classifiy_news_with_evidence_tool(input_str: str) -> str:
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
    return json.dumps({
        "input_user": input_str,
        "classification": classification,
        "evidence_scraped": scraped,
    }, ensure_ascii=False)

# === Initialize LLM ===
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
)

# === Register tools ===
tools = [
    Tool.from_function(
        func=classify_news_without_evidence_tool,
        name="klasifikasi_berita_tanpa_bukti",
        description="""
        Klasifikasikan berita tanpa bukti (perioritas utama jika tidak diminta bukti!). HANYA digunakan ketika:
        - User memberikan title DAN content
        - DAN user TIDAK meminta bukti / evidence / search

        JANGAN digunakan untuk input yang mengandung URL.
        Input format: 'title=Judul berita, content=Isi berita'
        """),
    Tool.from_function(
        func=get_evidence_tool,
        name="dapatkan_bukti",
        description="""Dapatkan bukti dari judul berita yang diberikan, HANYA digunakan ketika user meminta bukti untuk sebuah judul.
        Tidak menerima content.
        Tidak boleh dipakai untuk URL.
        berikan link link dari hasil pencarian Google, dan bukti yang di-scrape dari link tersebut. Input format: 'title=Judul berita'"""),
    Tool.from_function(
        func=classifiy_news_with_evidence_tool,
        name="klasifikasi_berita_dengan_bukti",
        description=("""Prediksi klasifikasi berita dengan pencarian bukti,HANYA digunakan ketika user meminta bukti DAN memberikan title + content.
            Jangan dipakai kalau tidak ada kata: bukti, evidence, atau verifikasi.
            (jika tidak diminta bukti, jangan dipakai) Input format: 'title(string)=Judul berita(string), content(string)=Isi berita(string)'"""
        )
    ),
    Tool.from_function(
        func=get_news_tool,
        name="cari_berita_dari_link",
        description=(
            "TOOL PRIORITAS UTAMA untuk setiap input yang mengandung URL. "
            "Jika user memberikan link/url berita, SELALU gunakan tool ini "
            "terlebih dahulu untuk mengambil judul dan isi berita. "
            "Input: 'URL berita'"
        )
    )
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
                """
                RULES FOR TOOL SELECTION (WAJIB DIPATUHI):
                1. Jika input user MENGANDUNG URL → SELALU gunakan tool: cari_berita_dari_link.
                Tidak boleh pakai tool lain sampai title+content berhasil diambil.
                2. Jika user memberikan TITLE dan CONTENT, dan TIDAK meminta bukti → gunakan:
                klasifikasi_berita_tanpa_bukti.
                3. Jika user meminta BUKTI (“bukti”, “evidence”, “search”, “cek kebenaran”) → gunakan:
                klasifikasi_berita_dengan_bukti.
                4. Jika user hanya memberikan TITLE dan meminta bukti → gunakan:
                dapatkan_bukti.
                5. Jangan pernah memanggil tool selain yang sesuai aturan di atas.
                6. Jika ragu, TANYAKAN dulu ke user, jangan asal pilih tool.
            """
            )
        )
    }
)


