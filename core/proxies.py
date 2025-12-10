import random
from core.config import config
from core.logger import logger

def get_proxy():
    """
    Selects a proxy from configuration when proxying is enabled.
    
    Returns:
        dict: Mapping with `"http"` and `"https"` set to the chosen proxy string, or `None` if proxies are disabled or no proxy list is available.
    """
    if not config.use_proxies:
        logger.info("Proxies are disabled in config. Not using any proxy.")
        return None

    proxies = config.get("proxy_list", [])
    if not proxies:
        logger.warning("Proxies are enabled but no proxy_list found in config. Not using any proxy.")
        return None
            
    proxy = random.choice(proxies)
    logger.info(f"Using proxy: {proxy}")
    return {
        "http": proxy,
        "https": proxy
    }

def get_random_user_agent():
    """
    Selects a user agent string at random from the configured list.
    
    If the configuration provides no user agents, returns a sensible default user agent string.
    
    Returns:
        str: A user agent string chosen from configuration, or a default string if none are configured.
    """
    user_agents = config.get("user_agents", [])
    if not user_agents:
        logger.warning("No user_agents found in config. Using a default user agent.")
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    return random.choice(user_agents)

if __name__ == '__main__':
    # For testing the proxy function
    # Note: For this to work correctly, you would need a settings.json
    # with "use_proxies": true and "proxy_list": ["http://your.proxy.com:8080"]
    test_proxy = get_proxy()
    if test_proxy:
        logger.info(f"Test using proxy: {test_proxy}")
    else:
        logger.info("Test: No proxies used or an error occurred.")
    
    test_ua = get_random_user_agent()
    logger.info(f"Test random user agent: {test_ua}")