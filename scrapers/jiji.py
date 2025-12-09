import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from core.filters import looks_like_gig
from core.storage import save_gig

BASE_URL = "https://jiji.ug/search?query=website"

def scrape_jiji():
    headers = {
        "User-Agent": UserAgent().random
    }

    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        ads = soup.find_all("article")

        for ad in ads:
            title = ad.get_text(strip=True)
            link = ad.find("a")

            if not link:
                continue

            href = "https://jiji.ug" + link.get("href")

            if looks_like_gig(title):
                save_gig(
                    source="Jiji",
                    title=title,
                    link=href,
                    snippet=title[:200]
                )

    except Exception as e:
        print(f"[JIJI ERROR] {e}")
