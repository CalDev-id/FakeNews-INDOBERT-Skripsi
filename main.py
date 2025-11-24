import json
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from agents.predict.predict import classify_berita
from agents.get_evidence.google_search import google_search
from agents.get_evidence.scrape_html import scrape_html
from agents.explanation.explanation import explanation
from agents.chat.chat import agent

#uvicorn main:app --reload
#uvicorn main:app --host 0.0.0.0 --port 8000

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "Fake News Detection API"}

class PredictRequest(BaseModel):
    title: str
    content: str

@app.post("/predict/")
def predict_fake_news(data: PredictRequest):
    result = classify_berita(data.title, data.content)
    return result

@app.post("/get_evidence/")
def get_evidence(
    data: PredictRequest,
):
    total_results: int = 10
    scrape_limit: int = 1
    query = data.title

    # 1. Google Search
    links = google_search(query, total_results=total_results)

    # 2. ScrapingBee
    scraped = []
    for url in links[:scrape_limit]:
        content = scrape_html(url)
        if content:
            scraped.append(content)

    return {
        "query": query,
        "total_google_results": len(links),
        "scraped_results": len(scraped),
        "links": links,
        "evidence": scraped
    }

@app.post("/predict_with_evidence/")
def predict_with_evidence(data: PredictRequest):

    classification = classify_berita(data.title, data.content)

    total_results = 10
    scrape_limit = 3
    links = google_search(data.title, total_results=total_results)

    scraped = []
    for url in links[:scrape_limit]:
        content = scrape_html(url)
        if content:
            scraped.append({
                "url": url,
                "content": content
            })

    llm_output = explanation(
        classification=classification,
        news_scrape=scraped,
        evidence_link=links,
        title=data.title,
        content=data.content
    )

    return {
        "input_user": {
            "title": data.title,
            "content": data.content,
        },
        "classification": classification,
        "evidence_links": links,
        "evidence_scraped": scraped,
        "explanation": llm_output 
    }
class UrlRequest(BaseModel):
    url: str
    
@app.post("/predict_from_url/")
def predict_from_url(data: UrlRequest):

    # 1. Scrape artikel dari URL input
    scraped_main = scrape_html(data.url)
    if not scraped_main or scraped_main.get("content") == "Tidak berhasil ekstrak isi artikel":
        return {
            "error": "Gagal mengambil artikel dari URL",
            "url": url
        }

    title = scraped_main.get("judul", "")
    content = scraped_main.get("content", "")

    # 2. Klasifikasi IndoBERT
    classification = classify_berita(title, content)

    # 3. Google Search untuk mendapatkan evidence
    total_results = 10
    scrape_limit = 1
    links = google_search(title, total_results=total_results)

    # 4. Scrape evidence dari link pencarian
    scraped_evidence = []
    for url in links[:scrape_limit]:
        ev = scrape_html(url)
        if ev:
            scraped_evidence.append({
                "url": url,
                "content": ev
            })

    # 5. LLM judgement
    llm_output = explanation(
        classification=classification,
        news_scrape=scraped_evidence,
        title=title,
        evidence_link=links,
        content=content
    )

    # 6. Output final
    return {
        "input_user": {
            "url": url,
            "title": title,
            "content": content
        },
        "classification": classification,
        "evidence_links": links,
        "evidence_scraped": scraped_evidence,
        "explanation": llm_output
    }

class ChatRequest(BaseModel):
    message: str

@app.post("/chat/")
def chat_endpoint(data: ChatRequest):
    user_message = data.message

    try:
        response = agent.run(user_message)
        return {
            "response": response
        }
    except Exception as e:
        return {"error": str(e)}