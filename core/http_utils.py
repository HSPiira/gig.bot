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
    Fetches a URL using the provided requests method and applies the module's retryable error handling.
    
    Defaults the request timeout from config.http_timeout when not supplied in kwargs. Retries for network timeouts, connection errors, and specific HTTP status codes are handled by the surrounding retry configuration; this function raises request-related exceptions to allow that behavior.
    
    Parameters:
        method (callable): A requests method function (e.g., requests.get, requests.post).
        url (str): The URL to request.
        **kwargs: Additional keyword arguments forwarded to the requests method; `timeout` defaults to config.http_timeout if omitted.
    
    Returns:
        requests.Response: The HTTP response when the request completes successfully.
    
    Raises:
        requests.exceptions.RequestException: If the request fails (re-raised to surface network or HTTP errors).
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