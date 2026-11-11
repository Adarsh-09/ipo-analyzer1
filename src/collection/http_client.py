"""
IPOVision HTTP Client
Provides a reliable, rate-limited HTTP session for all data collection activities.

Purpose:
    This module wraps Python's `requests.Session` with defensive defaults that every
    scraper in the project should use. It handles:
    - Consistent browser-like User-Agent headers so servers don't reject us.
    - Configurable timeouts so the program never hangs on a dead connection.
    - Automatic retries with exponential backoff for transient network failures.
    - Rate limiting (minimum delay between requests) to respect server capacity.
    - Structured error handling that logs failures without crashing the pipeline.

Data Flow:
    Calling code  -->  IPOHttpClient.get(url)  -->  requests.Session
                                                      |
                                                      v
                                               Rate limiter (sleep)
                                                      |
                                                      v
                                               HTTP GET with headers
                                                      |
                                                      v
                                               Response or error dict

How to Use:
    from src.collection.http_client import IPOHttpClient

    client = IPOHttpClient()
    result = client.get("https://example.com/ipo-data")
    if result["success"]:
        html = result["text"]
    else:
        print(f"Failed: {result['error']}")
"""

import time
import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class IPOHttpClient:
    """
    A defensive HTTP client with rate limiting, retries, and structured responses.

    Every scraper module should use an instance of this class rather than calling
    `requests.get()` directly. This ensures consistent behaviour across the project.

    Attributes:
        session: The underlying requests.Session with retry adapter mounted.
        delay: Minimum seconds between consecutive requests (rate limiter).
        timeout: Seconds to wait for a server response before giving up.
    """

    def __init__(
        self,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        timeout: int = 15,
        max_retries: int = 3,
        rate_limit_delay: float = 2.0,
        verify_ssl: bool = True,
    ):
        """
        Initialise the HTTP client.

        Args:
            user_agent: Browser-like User-Agent string. Servers often block
                        requests that use the default Python UA.
            timeout: Maximum seconds to wait for a response.
            max_retries: Number of retry attempts for 5xx errors and connection
                         failures. Uses exponential backoff.
            rate_limit_delay: Minimum seconds between consecutive requests to
                              avoid overwhelming the server.
            verify_ssl: Whether to verify SSL certificates. Keep True unless
                        you have a specific, documented reason.
        """
        self.timeout = timeout
        self.delay = rate_limit_delay
        self.verify_ssl = verify_ssl
        self._last_request_time: float = 0.0

        # Build session with retry strategy
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        # Retry strategy: retry on 500, 502, 503, 504 only
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,  # 1s, 2s, 4s between retries
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _rate_limit(self) -> None:
        """
        Enforce minimum delay between requests.

        Why this matters:
            Sending requests too rapidly can get our IP blocked and puts
            unnecessary load on public servers. The delay is measured from
            the START of the previous request, not the end.
        """
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            sleep_time = self.delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform a GET request with rate limiting and error handling.

        Returns a structured dictionary rather than raising exceptions, so
        calling code can handle failures gracefully without try/except blocks
        everywhere.

        Args:
            url: The URL to fetch.
            params: Optional query parameters.
            extra_headers: Additional headers to merge for this specific request.

        Returns:
            dict with keys:
                - success (bool): Whether the request completed without error.
                - status_code (int or None): HTTP status code if a response was received.
                - text (str or None): Response body text on success.
                - content (bytes or None): Raw response bytes on success.
                - url (str): The requested URL (for logging).
                - headers (dict or None): Response headers on success.
                - content_type (str or None): Content-Type header value.
                - elapsed_ms (float or None): Round-trip time in milliseconds.
                - error (str or None): Error description on failure.
        """
        self._rate_limit()
        self._last_request_time = time.time()

        result = {
            "success": False,
            "status_code": None,
            "text": None,
            "content": None,
            "url": url,
            "headers": None,
            "content_type": None,
            "elapsed_ms": None,
            "error": None,
        }

        headers = {}
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            result["status_code"] = response.status_code
            result["headers"] = dict(response.headers)
            result["content_type"] = response.headers.get("Content-Type", "")
            result["elapsed_ms"] = response.elapsed.total_seconds() * 1000

            if response.status_code == 200:
                result["success"] = True
                result["text"] = response.text
                result["content"] = response.content
            else:
                result["error"] = f"HTTP {response.status_code}"
                logger.warning(f"Non-200 response from {url}: {response.status_code}")

        except requests.exceptions.Timeout:
            result["error"] = "Request timed out"
            logger.error(f"Timeout fetching {url}")
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {e}"
            logger.error(f"Connection error fetching {url}: {e}")
        except requests.exceptions.TooManyRedirects:
            result["error"] = "Too many redirects"
            logger.error(f"Redirect loop at {url}")
        except requests.exceptions.RequestException as e:
            result["error"] = f"Request failed: {e}"
            logger.error(f"Request exception for {url}: {e}")

        return result

    def head(self, url: str) -> Dict[str, Any]:
        """
        Perform a HEAD request to check URL availability without downloading content.
        Useful for testing PDF download links before committing to a full download.
        """
        self._rate_limit()
        self._last_request_time = time.time()

        result = {
            "success": False,
            "status_code": None,
            "url": url,
            "headers": None,
            "content_type": None,
            "content_length": None,
            "error": None,
        }

        try:
            response = self.session.head(
                url, timeout=self.timeout, verify=self.verify_ssl, allow_redirects=True
            )
            result["status_code"] = response.status_code
            result["headers"] = dict(response.headers)
            result["content_type"] = response.headers.get("Content-Type", "")
            result["content_length"] = response.headers.get("Content-Length")
            result["success"] = response.status_code == 200

            if not result["success"]:
                result["error"] = f"HTTP {response.status_code}"

        except requests.exceptions.RequestException as e:
            result["error"] = f"HEAD request failed: {e}"
            logger.error(f"HEAD request failed for {url}: {e}")

        return result

