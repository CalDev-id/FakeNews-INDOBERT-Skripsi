import asyncio
from fastapi import APIRouter
# from schemas.predict import PredictRequest, ClaimRequest, UrlRequest
from agents.predict.predict import classify_berita, advance_classify_berita
from agents.get_evidence.google_search import google_search
from agents.get_evidence.scrape_html import scrape_html
from agents.explanation.explanation import explanation
from agents.claim_check.claim_check import claim_check
from pydantic import BaseModel

router = APIRouter(tags=["Prediction"])

class PredictRequest(BaseModel):
    title: str
    content: str

@router.post("/predict/")
def predict_fake_news(data: PredictRequest):
    result = classify_berita(data.title, data.content)
    return result

class ClaimRequest(BaseModel):
    claim: str

@router.post("/get_evidence/")
def get_evidence(
    data: ClaimRequest,
):
    total_results: int = 10
    scrape_limit: int = 1  # cuma mau 1 evidence
    query = data.claim
    # 1. Google Search
    links = google_search(query, total_results=total_results)

    # 2. Scraping dengan fallback ke link berikutnya
    scraped = []

    for url in links:  # cek semua link
        if len(scraped) >= scrape_limit:
            break  # sudah cukup evidence

        content = scrape_html(url)

        if content is None:
            print(f"❌ Gagal scrape → {url}")
            continue  # coba link berikutnya

        print(f"✅ Berhasil scrape → {url}")
        scraped.append(content)

    return {
        "query": query,
        "total_google_results": len(links),
        "scraped_results": len(scraped),
        "links": links,
        "evidence": scraped
    }


@router.post("/predict_with_evidence/")
def predict_with_evidence(data: PredictRequest):
    total_results = 10
    scrape_limit = 1
    links = google_search(data.title, total_results=total_results)

    scraped = []
    for url in links:
        if len(scraped) >= scrape_limit:
            break
        content = scrape_html(url)
        if content is None:
            print(f"❌ Gagal scrape → {url}")
            continue
        print(f"✅ Berhasil scrape → {url}")
        scraped.append(content)

    classification = classify_berita(data.title, data.content)

    advance_classification = advance_classify_berita(
        classification=classification,
        news_scrape=scraped,
        title=data.title,
        evidence_link=links,
        content=content
    )

    llm_output = explanation(
        classification=classification,
        news_scrape=scraped,
        evidence_link=links,
        title=data.title,
        content=data.content
    )

    return {
        "url": scraped[0].get("link", "") if scraped else "",
        "title": data.title,
        "content": data.content,
        "classification": advance_classification,
        "evidence_links": links,
        "evidence_scraped": scraped,
        "explanation": llm_output 
    }

class UrlRequest(BaseModel):
    url: str
    
@router.post("/predict_from_url/")
def predict_from_url(data: UrlRequest):

    # 1. Scrape artikel dari URL input
    scraped_main = scrape_html(data.url)
    if not scraped_main or scraped_main.get("content") == "Tidak berhasil ekstrak isi artikel":
        return {
            "error": "Gagal mengambil artikel dari URL",
            "url": data.url
        }

    title = scraped_main.get("judul", "")
    content = scraped_main.get("content", "")

    # 2. Klasifikasi IndoBERT
    classification = classify_berita(title, content)

    # 3. Google Search
    total_results = 10
    scrape_limit = 1
    links = google_search(title, total_results=total_results)

    # 4. Scrape evidence
    scraped_evidence = []
    for url in links:  # cek semua link
        if len(scraped_evidence) >= scrape_limit:
            break  # sudah cukup evidence

        content = scrape_html(url)

        if content is None:
            print(f"❌ Gagal scrape → {url}")
            continue  # coba link berikutnya

        print(f"✅ Berhasil scrape → {url}")
        scraped_evidence.append(content)

    # 5. Advance Classification
    advance_classification = advance_classify_berita(
        classification=classification,
        news_scrape=scraped_evidence,
        title=title,
        evidence_link=links,
        content=content
    )

    # 6. LLM judgement
    llm_output = explanation(
        classification=advance_classification,
        news_scrape=scraped_evidence,
        title=title,
        evidence_link=links,
        content=content
    )

    # 7. Output final
    return {
        "url": data.url,
        "title": title,
        "content": content,
        "classification": advance_classification,
        "evidence_links": links,
        "evidence_scraped": scraped_evidence,
        "explanation": llm_output
    }

    
@router.post("/predict_from_claim/")
def predict_from_claim(data: ClaimRequest):

    total_results: int = 10
    scrape_limit: int = 1
    query = data.claim

    links = google_search(query, total_results=total_results)

    claim_checked = claim_check(data.claim, links)

    if "sesuai" not in claim_checked.lower():
        return {
            "url": "",
            "title": "",
            "content": "",
            "classification": {
                "final_label": "unknown",
                "final_confidence": 0,
                "error": "Claim tidak dapat diverifikasi dengan sumber yang ada: " + claim_checked
            },
            "evidence_links": links,
            "evidence_scraped": [],
            "explanation": "Claim tidak dapat diverifikasi dengan sumber yang ada: " + claim_checked
        }

    scraped = []
    for url in links:
        if len(scraped) >= scrape_limit:
            break
        content = scrape_html(url)
        if content is None:
            print(f"❌ Gagal scrape → {url}")
            continue
        print(f"✅ Berhasil scrape → {url}")
        scraped.append(content)

    classification = classify_berita(scraped[0].get("judul", ""), scraped[0].get("content", ""))

    advance_classification = advance_classify_berita(
        classification=classification,
        news_scrape=scraped,
        title=scraped[0].get("judul", ""),
        evidence_link=links,
        content=scraped[0].get("content", "")
    )

    llm_output = explanation(
        classification=advance_classification,
        news_scrape=scraped,
        title=scraped[0].get("judul", ""),
        evidence_link=links,
        content=scraped[0].get("content", "")
    )

    return {
        "url": links[0] if links else "",
        "title": scraped[0].get("judul", "") if scraped else "",
        "content": scraped[0].get("content", "") if scraped else "",
        "classification": advance_classification,
        "evidence_links": links,
        "evidence_scraped": scraped,
        "explanation": llm_output
    }

@router.post("/predict_test/")
async def predict_test(data: UrlRequest):
    await asyncio.sleep(5)

    return {
        "url": "https://www.liputan6.com/global/read/2175314/ditemukan-fosil-manusia-kembar-tertua-di-dunia",
  "title": "Ditemukan: Fosil Manusia Kembar Tertua di Dunia",
  "content": "Satu set fosil manusia purba ditemukan dalam sebuah penggalian.\nLiputan6.com, Rusia- Seorang bio-arkeolog Saskatchewan mengemukakan bahwa ia telah menemukan fosil manusia kembar tertua di sebuah pemakaman Siberia. Angela Lieverse, sang arkeolog mengatakan bahwa kerangka tersebut digali dari seorang ibu dan anak kembarnya yang berusia sekitar 7.700 tahun. Fosil wanita tersebut diperkirakan meninggal dalam kondisi hamil tua. Penyebabnya bisa jadi karena pendarahan atau kelelahan saat menjelang melahirkan. Namun sang bayi yang dinyatakan kembar, salah satunya berada dalam posisi sungsang, yang menghambat kelahiran anak kedua. Dilansir melalui jurnal Antiquity, Jumat (13/2/2015), para ilmuwan menganggap anak kembar hanya ada dalam pasangan moderen dan meragukan keabsahannya di masa lalu. Kini, dengan adanya penemuan fosil bayi kembar tersebut membuktikan bahwa anak kembar pun eksis sejak jaman purba. Sebelum menemukan fosil wanita beserta anak kekmbarnya ini, set yang sama pernah ditemukan di South Dakota, Amerika Serikat beberapa waktu yang lalu. Usia fosil tersebut diperkirakan 400 tahun. ( Liz )\nCopyright © 2025 Liputan6.com KLY KapanLagi Youniverse All Right Reserved.",
  "classification": {
    "final_label": "valid",
    "final_confidence": 78.5
  },
  "evidence_links": [
    "https://www.liputan6.com/global/read/2175314/ditemukan-fosil-manusia-kembar-tertua-di-dunia",
    "https://e-journal.unair.ac.id/MOG/article/download/14507/8031/51258",
    "https://repository.unair.ac.id/view/subjects/R5-920.html",
    "https://www.bbc.com/indonesia/vert-tra-60427392",
    "https://www.merdeka.com/teknologi/mumi-remaja-mesir-kuno-ditemukan-meninggal-saat-mengandung-bayi-kembar-74538-mvk.html",
    "https://id.scribd.com/document/747590311/Modified-4",
    "https://www.detik.com/bali/berita/d-6560608/300-bio-wa-cuek-aesthetic-dan-beda-dari-yang-lain",
    "https://www.kompas.com/tren/read/2023/06/09/100000165/benarkah-sering-tidur-telentang-bikin-kepala-bayi-datar-atau-peyang-?page=all",
    "https://huggingface.co/fathan/indojave-codemixed-bert-base/raw/main/vocab.txt",
    "https://www.lemon8-app.com/discover/acara%20tujuh%20bulanan%20kehamilan?region=id"
  ],
  "evidence_scraped": [
    {
      "judul": "Ditemukan: Fosil Manusia Kembar Tertua di Dunia",
      "tanggal": "4 jam lalu",
      "sumber": "liputan6.com",
      "link": "https://www.liputan6.com/global/read/2175314/ditemukan-fosil-manusia-kembar-tertua-di-dunia",
      "content": "Satu set fosil manusia purba ditemukan dalam sebuah penggalian.\nLiputan6.com, Rusia- Seorang bio-arkeolog Saskatchewan mengemukakan bahwa ia telah menemukan fosil manusia kembar tertua di sebuah pemakaman Siberia. Angela Lieverse, sang arkeolog mengatakan bahwa kerangka tersebut digali dari seorang ibu dan anak kembarnya yang berusia sekitar 7.700 tahun. Fosil wanita tersebut diperkirakan meninggal dalam kondisi hamil tua. Penyebabnya bisa jadi karena pendarahan atau kelelahan saat menjelang melahirkan. Namun sang bayi yang dinyatakan kembar, salah satunya berada dalam posisi sungsang, yang menghambat kelahiran anak kedua. Dilansir melalui jurnal Antiquity, Jumat (13/2/2015), para ilmuwan menganggap anak kembar hanya ada dalam pasangan moderen dan meragukan keabsahannya di masa lalu. Kini, dengan adanya penemuan fosil bayi kembar tersebut membuktikan bahwa anak kembar pun eksis sejak jaman purba. Sebelum menemukan fosil wanita beserta anak kekmbarnya ini, set yang sama pernah ditemukan di South Dakota, Amerika Serikat beberapa waktu yang lalu. Usia fosil tersebut diperkirakan 400 tahun. ( Liz )\nCopyright © 2025 Liputan6.com KLY KapanLagi Youniverse All Right Reserved.",
      "featured_image": "https://cdn1-production-images-kly.akamaized.net/FMDwWDXcjXNAH9mO844ywM0zT-8=/1200x675/smart/filters:quality(75):strip_icc():format(jpeg)/kly-media-production/medias/810502/original/077247100_1423801517-bonesasdfasdf.jpg"
    }
  ],
  "explanation": "Kesimpulan: Valid (bukan hoaks)\n\nAlasan singkat:\n- Klaim didukung oleh liputan media arus utama (mis. Liputan6) yang merujuk pada publikasi ilmiah (jurnal Antiquity) dan nama peneliti nyata (Angela Lieverse). Hasil scraping menunjukkan artikel Liputan6 yang mengutip Antiquity (13/2/2015) tentang kerangka seorang ibu dan janin kembar berusia sekitar 7.700 tahun dari Siberia.\n- Adanya rujukan ke jurnal/publikasi akademik (Antiquity) menjadikan klaim ini berdasar pada temuan arkeologis/osteologis, bukan sekadar desas-desus.\n- Beberapa tautan dalam daftar bukti tidak relevan atau salah konteks (mis. detik.com yang tampak tidak terkait, Scribd, lemon8, dll), namun itu tidak menghapus bukti utama dari laporan akademik dan liputan media.\n\nCatatan penting / keterbatasan:\n- Interpretasi fosil selalu dapat diperdebatkan dalam komunitas ilmiah; klaim “tertua di dunia” bergantung pada penafsiran data dan perbandingan dengan temuan lain. Namun, berdasarkan sumber yang ada, klaim bahwa ditemukan bukti kembar purba tersebut adalah sah dan dilaporkan secara ilmiah.\n- Jika ingin membagikan berita ini, disarankan menyertakan referensi ke publikasi asli (Antiquity) atau sumber akademik untuk konteks lebih lengkap.\n\nKepercayaan penilaian: sekitar 80% (sejalan dengan hasil model IndoBERT yang diberikan: \"valid\" 78.5%)."
    }

