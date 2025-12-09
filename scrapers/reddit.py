import requests
from core.filters import looks_like_gig
from core.storage import save_gig
from core.proxies import get_proxy

# A list of subreddits to scrape
SUBREDDITS = [
    "forhire",
    "jobbit",
    "jobsearch",
    "hiring"
]
BASE_URL = "https://www.reddit.com/r/{subreddit}/search.json?q=flair%3A%22Hiring%22&restrict_sr=on&sort=new"

def scrape_reddit():
    """
    Scrapes a list of subreddits for posts with the "Hiring" flair.
    """
    print("Scraping Reddit...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    proxy = get_proxy()

    for subreddit in SUBREDDITS:
        print(f"-> Scraping subreddit: r/{subreddit}")
        url = BASE_URL.format(subreddit=subreddit)
        
        try:
            response = requests.get(url, headers=headers, proxies=proxy)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            if not posts:
                print(f"No posts found in r/{subreddit}.")
                continue

            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title")
                text = post_data.get("selftext")
                link = "https://www.reddit.com" + post_data.get("permalink", "")
                
                content = f"{title} {text}"

                if looks_like_gig(content):
                    save_gig(f"Reddit (r/{subreddit})", title, link, text[:255])

        except requests.exceptions.RequestException as e:
            print(f"Error scraping r/{subreddit}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during r/{subreddit} scraping: {e}")

if __name__ == '__main__':
    from core.storage import init_db
    init_db()
    scrape_reddit()