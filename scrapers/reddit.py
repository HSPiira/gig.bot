import requests
from core.filters import looks_like_gig
from core.storage import save_gig
from core.proxies import get_proxy

# Reddit API endpoint for the /r/forhire subreddit, searching for "Hiring" flair
# Note: Reddit's search via URL parameter is limited, but this is a good starting point.
# For more robust searching, the official Reddit API with PRAW would be better.
SUBREDDIT_URL = "https://www.reddit.com/r/forhire/search.json?q=flair%3A%22Hiring%22&restrict_sr=on&sort=new"

def scrape_reddit():
    """
    Scrapes the /r/forhire subreddit for posts with the "Hiring" flair.
    """
    print("Scraping Reddit...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }

    proxy = get_proxy()

    try:
        response = requests.get(SUBREDDIT_URL, headers=headers, proxies=proxy)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = response.json()
        posts = data.get("data", {}).get("children", [])

        if not posts:
            print("No posts found on Reddit.")
            return

        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title")
            text = post_data.get("selftext")
            link = "https://www.reddit.com" + post_data.get("permalink")
            
            content = f"{title} {text}"

            if looks_like_gig(content):
                save_gig("Reddit", title, link, text[:255]) # Save a snippet

    except requests.exceptions.RequestException as e:
        print(f"Error scraping Reddit: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during Reddit scraping: {e}")

if __name__ == '__main__':
    # For testing the scraper directly
    from core.storage import init_db
    init_db()
    scrape_reddit()