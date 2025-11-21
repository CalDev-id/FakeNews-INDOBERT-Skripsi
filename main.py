import json
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from agents.predict.predict import classify_berita
from agents.get_evidence.google_search import google_search
from agents.get_evidence.scrape_html import scrape_html
from agents.explanation.explanation import explanation

#uvicorn main:app --reload
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

    # 1. Model IndoBERT classification
    classification = classify_berita(data.title, data.content)

    # 2. Google Search
    total_results = 10
    scrape_limit = 2
    links = google_search(data.title, total_results=total_results)

    # 3. Scrape evidence
    scraped = []
    for url in links[:scrape_limit]:
        content = scrape_html(url)
        if content:
            scraped.append({
                "url": url,
                "content": content
            })

    # 4. Final judgement by LLM
    llm_output = explanation(
        classification=classification,
        news_scrape=scraped,
        title=data.title,
        content=data.content
    )

    # 5. Output JSON final
    return {
        "input_user": {
            "title": data.title,
            "content": data.content,
        },
        "evidence_links": links,
        "evidence_scraped": scraped,
        "explanation": llm_output  # LLM output JSON
    }