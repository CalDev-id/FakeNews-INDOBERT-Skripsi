import json
from llm.groq_runtime import GroqRunTime
from llm.gpt_runtime import GPTRunTime

def explanation(classification, news_scrape, title, evidence_link, content):
    groq_runtime = GroqRunTime()
    gpt_runtime = GPTRunTime()

    system_prompt = """Kamu adalah asisten AI yang menilai apakah suatu berita tergolong hoaks atau valid.
Gunakan hasil klasifikasi IndoBERT dan hasil scraping berita dari internet sebagai referensi.
"""

    user_prompt = f"""
Berikut adalah berita yang ingin diklasifikasikan:

Judul: {title}

Hasil klasifikasi IndoBERT:
{json.dumps(classification, ensure_ascii=False, indent=2)}
(kadang hasil klasifikasi bisa salah, jadi tentukan berdasarkan bukti yang ada)

Link bukti yang ditemukan:
{json.dumps(evidence_link, ensure_ascii=False, indent=2)}

Hasil scraping berita referensi:
{json.dumps(news_scrape, ensure_ascii=False, indent=2)}

Tentukan apakah berita ini hoaks atau valid berdasarkan konteks dan kesesuaian dengan berita referensi.
"""

    # response = groq_runtime.generate_response(system_prompt, user_prompt)
    response = gpt_runtime.generate_response(system_prompt, user_prompt)
    return response
