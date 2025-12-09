import random

PROXY_FILE = "proxies.txt"

def get_proxy():
    """
    Reads the proxy list from PROXY_FILE and returns a random proxy.
    """
    try:
        with open(PROXY_FILE, "r") as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        if not proxies:
            return None
            
        proxy = random.choice(proxies)
        return {
            "http": proxy,
            "https": proxy
        }
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading proxy file: {e}")
        return None

if __name__ == '__main__':
    # For testing the proxy function
    proxy = get_proxy()
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxies found or an error occurred.")
