import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from core.filters import looks_like_gig
from core.storage import save_gig
from core.proxies import get_proxy

BASE_URL = "https://jiji.ug/search?query=website"

def scrape_jiji():
    headers = {
        "User-Agent": UserAgent().random
    }
    
    proxy = get_proxy()

    try:
        print("Scraping Jiji...")
        response = requests.get(BASE_URL, headers=headers, proxies=proxy, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        ads = soup.find_all("div", class_="b-list-advert__item")

        for ad in ads:
            title_element = ad.find("div", class_="b-list-advert__item-title")
            title = title_element.get_text(strip=True) if title_element else "No Title"

            link_element = ad.find("a", class_="b-list-advert__item-title-link")
            if not link_element:
                continue
            
            href = "https://jiji.ug" + link_element.get("href")

            if looks_like_gig(title):
                save_gig(
                    source="Jiji",
                    title=title,
                    link=href,
                    snippet=title[:200]
                )

    except Exception as e:
        print(f"[JIJI ERROR] {e}")
