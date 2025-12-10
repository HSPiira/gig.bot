import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.logger import logger
from core.config import config # Import config

@retry(
    stop=stop_after_attempt(config.retry_attempts), # Use retry_attempts from config
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=(
        retry_if_exception_type(requests.exceptions.Timeout) |
        retry_if_exception_type(requests.exceptions.ConnectionError) |
        retry_if_exception_type(requests.exceptions.RequestException)
    ),
    reraise=True
)
def fetch_url_with_retries(method, url, **kwargs):
    """
    Fetches a URL with retry logic for timeouts and specific HTTP status codes.

    Args:
        method: The HTTP method to use (e.g., requests.get, requests.post).
        url: The URL to fetch.
        **kwargs: Additional arguments to pass to the requests method.

    Returns:
        requests.Response: The response object if successful.

    Raises:
        requests.exceptions.RequestException: If the request fails after all retries.
    """
    # Set default timeout from config if not provided in kwargs
    kwargs.setdefault('timeout', config.http_timeout)
    
    try:
        logger.info(f"Attempting to {method.__name__.upper()} {url} with kwargs: {kwargs}")
        response = method(url, **kwargs)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [429, 500, 502, 503]:
            logger.warning(f"Retryable HTTP error encountered: {e.response.status_code} for {url}. Retrying...")
            raise # Re-raise to trigger tenacity retry
        else:
            logger.error(f"Non-retryable HTTP error encountered: {e.response.status_code} for {url}. Giving up.")
            raise
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logger.warning(f"Network error encountered for {url}: {e}. Retrying...")
        raise # Re-raise to trigger tenacity retry
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected request error occurred for {url}: {e}. Giving up.")
        raise
