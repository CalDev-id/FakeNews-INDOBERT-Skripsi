import json
from llm.groq_runtime import GroqRunTime

def explanation(classification, news_scrape, title, content):
    groq_runtime = GroqRunTime()

    system_prompt = """Kamu adalah asisten AI yang menilai apakah suatu berita tergolong hoaks atau valid.
Gunakan hasil klasifikasi IndoBERT dan hasil scraping berita dari internet sebagai referensi.
Berikan output JSON dengan atribut:
- "label": "hoaks" atau "valid"
- "confidence": (0-100)
- "reason": penjelasan singkat."""

    user_prompt = f"""
Berikut adalah berita yang ingin diklasifikasikan:

Judul: {title}

Hasil klasifikasi IndoBERT:
{json.dumps(classification, ensure_ascii=False, indent=2)}

Hasil scraping berita referensi:
{json.dumps(news_scrape, ensure_ascii=False, indent=2)}

Tentukan apakah berita ini hoaks atau valid berdasarkan konteks dan kesesuaian dengan berita referensi.
"""

    response = groq_runtime.generate_response(system_prompt, user_prompt)
    return response
