import re
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

load_dotenv()
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")


def scrape_html(url):
    """Scrape hanya featured image + metadata artikel."""
    try:
        api_url = "https://app.scrapingbee.com/api/v1/"
        params = {
            "api_key": SCRAPINGBEE_API_KEY,
            "url": url,
            "render_js": "true",
            "block_ads": "true",
            "wait": "4000"
        }

        response = requests.get(api_url, params=params, timeout=100)

        if response.status_code != 200:
            print("ScrapingBee error:", response.text)
            return None

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # ====== Judul ======
        judul = soup.title.string.strip() if soup.title and soup.title.string else "Unknown"

        # ====== Tanggal ======
        time_tag = soup.find("time")
        tanggal = time_tag.get_text(strip=True) if time_tag else "Unknown"

        # ====== Content ======
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paragraphs = [p for p in paragraphs if len(p) > 50]

        content = "\n".join(paragraphs) if paragraphs else "Tidak berhasil ekstrak isi artikel"

        # ===========================================================
        #                     FEATURED IMAGE ONLY
        # ===========================================================

        featured_image = None

        # 1️⃣ Cek meta og:image
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            featured_image = urljoin(url, og["content"])

        # 2️⃣ Cek meta twitter:image
        if not featured_image:
            twitter = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter and twitter.get("content"):
                featured_image = urljoin(url, twitter["content"])

        # 3️⃣ Cek JSON-LD schema
        if not featured_image:
            json_ld_tags = soup.find_all("script", type="application/ld+json")
            for tag in json_ld_tags:
                try:
                    import json
                    data = json.loads(tag.string)

                    if isinstance(data, dict):
                        image = data.get("image")
                        if isinstance(image, str):
                            featured_image = urljoin(url, image)
                            break
                        if isinstance(image, dict) and "url" in image:
                            featured_image = urljoin(url, image["url"])
                            break
                        if isinstance(image, list) and len(image) > 0:
                            featured_image = urljoin(url, image[0])
                            break
                except:
                    pass

        # 4️⃣ Fallback: Ambil gambar pertama yang tampak besar di halaman
        if not featured_image:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if not src:
                    continue

                full_url = urljoin(url, src)
                if full_url.endswith((".svg", ".gif")):
                    continue

                featured_image = full_url
                break

        # ====== Return ======
        return {
            "judul": judul,
            "tanggal": tanggal,
            "sumber": urlparse(url).netloc.replace("www.", ""),
            "link": url,
            "content": content,
            "featured_image": featured_image,  # hanya ini!
        }

    except Exception as e:
        print(f"⚠️ Gagal scrape {url}: {e}")
        return None
