"""API client for external AI service with enhanced error handling and configuration."""
import requests
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time
from config import AI_API_BASE_URL, AI_API_TOKEN
from strings.instruction import Instruction

logger = logging.getLogger(__name__)


class AI_APIErrorType(Enum):
    """Types of API errors for better error categorization."""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class AI_APIConfig:
    """API configuration with defaults."""
    base_url: str = AI_API_BASE_URL
    token: str = AI_API_TOKEN
    model: str = "@cf/meta/llama-4-scout-17b-16e-instruct"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    fallback_message: str = "Oops! Sorry what did u say? 😜"


@dataclass
class AI_APIResponse:
    """Structured API response with metadata."""
    success: bool
    content: str
    error_type: Optional[AI_APIErrorType] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None


class AIAPIClient:
    """Enhanced AI API client with robust error handling and retry logic."""

    def __init__(self, config: Optional[AI_APIConfig] = None):
        self.config = config or AI_APIConfig()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured requests session with connection pooling."""
        session = requests.Session()
        if self.config.token:
            session.headers.update({
                "Authorization": f"Bearer {self.config.token}",
                "Content-Type": "application/json",
                "User-Agent": "NinjaSecret-Bot/1.0"
            })
        else:
            session.headers.update({
                "Content-Type": "application/json",
                "User-Agent": "NinjaSecret-Bot/1.0"
            })
        return session

    def get_response(self, user_message: str) -> str:
        """Get AI response with comprehensive error handling."""
        api_response = self._make_request_with_retry(user_message)

        if api_response.success:
            logger.info(
                "AI API request successful%s",
                f" in {api_response.response_time:.2f}s" if api_response.response_time else "",
            )
            return api_response.content

        self._log_error(api_response)
        return self.config.fallback_message

    def _make_request_with_retry(self, user_message: str) -> AI_APIResponse:
        """Make API request with retry logic."""
        last_response: Optional[AI_APIResponse] = None

        for attempt in range(self.config.max_retries):
            try:
                response = self._make_single_request(user_message)

                if response.success or response.error_type not in [
                    AI_APIErrorType.NETWORK_ERROR,
                    AI_APIErrorType.TIMEOUT_ERROR,
                    AI_APIErrorType.SERVER_ERROR,
                ]:
                    return response

                last_response = response

                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        "Retrying AI API request in %ss (attempt %s)", delay, attempt + 1
                    )
                    time.sleep(delay)

            except Exception as e:
                logger.error("Unexpected error during AI API request: %s", e)
                last_response = AI_APIResponse(
                    success=False,
                    content="",
                    error_type=AI_APIErrorType.UNKNOWN_ERROR,
                )

        return last_response or AI_APIResponse(
            success=False,
            content="",
            error_type=AI_APIErrorType.UNKNOWN_ERROR,
        )

    def _make_single_request(self, user_message: str) -> AI_APIResponse:
        """Make single API request with timing and error handling."""
        start_time = time.time()

        payload = self._build_payload(user_message)
        url = f"{self.config.base_url}{self.config.model}"

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout,
            )

            response_time = time.time() - start_time

            return self._process_response(response, response_time)

        except requests.exceptions.Timeout:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.TIMEOUT_ERROR,
                response_time=time.time() - start_time,
            )
        except requests.exceptions.ConnectionError:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.NETWORK_ERROR,
                response_time=time.time() - start_time,
            )
        except requests.exceptions.RequestException:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.NETWORK_ERROR,
                response_time=time.time() - start_time,
            )

    def _build_payload(self, user_message: str) -> Dict[str, Any]:
        """Build API request payload."""
        return {
            "messages": [
                {"role": "system", "content": Instruction.system_prompt()},
                {"role": "user", "content": user_message},
            ]
        }

    def _process_response(self, response: requests.Response, response_time: float) -> AI_APIResponse:
        """Process HTTP response and extract content."""
        try:
            data = response.json()
        except ValueError:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.INVALID_RESPONSE,
                status_code=response.status_code if hasattr(response, "status_code") else None,
                response_time=response_time,
            )

        if response.status_code == 401:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.AUTH_ERROR,
                status_code=response.status_code,
                response_time=response_time,
            )
        elif response.status_code == 429:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.RATE_LIMIT_ERROR,
                status_code=response.status_code,
                response_time=response_time,
            )
        elif response.status_code >= 500:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.SERVER_ERROR,
                status_code=response.status_code,
                response_time=response_time,
            )
        elif not response.ok:
            return AI_APIResponse(
                success=False,
                content="",
                error_type=AI_APIErrorType.UNKNOWN_ERROR,
                status_code=response.status_code,
                response_time=response_time,
            )

        if data.get("success", False):
            content = data.get("result", {}).get("response", "")
            if content:
                return AI_APIResponse(
                    success=True,
                    content=content,
                    status_code=response.status_code,
                    response_time=response_time,
                )

        return AI_APIResponse(
            success=False,
            content="",
            error_type=AI_APIErrorType.INVALID_RESPONSE,
            status_code=response.status_code,
            response_time=response_time,
        )

    def _log_error(self, api_response: AI_APIResponse) -> None:
        """Log API errors with appropriate detail level."""
        error_messages = {
            AI_APIErrorType.NETWORK_ERROR: "Network connection failed",
            AI_APIErrorType.TIMEOUT_ERROR: f"Request timed out after {self.config.timeout}s",
            AI_APIErrorType.AUTH_ERROR: "Authentication failed - check API token",
            AI_APIErrorType.RATE_LIMIT_ERROR: "Rate limit exceeded - too many requests",
            AI_APIErrorType.SERVER_ERROR: f"Server error (HTTP {api_response.status_code})",
            AI_APIErrorType.INVALID_RESPONSE: "Invalid or empty response from API",
            AI_APIErrorType.UNKNOWN_ERROR: "Unknown error occurred",
        }

        message = error_messages.get(api_response.error_type, "Unexpected error")

        if api_response.response_time:
            message += f" (took {api_response.response_time:.2f}s)"

        logger.error("AI API request failed: %s", message)

    def health_check(self) -> bool:
        """Check API health with a simple test request."""
        try:
            response = self._make_single_request("Hello")
            return response.success
        except Exception:
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()


# Singleton instance for easy access
_ai_client_instance: Optional[AIAPIClient] = None


def get_ai_api_client() -> AIAPIClient:
    """Get singleton AI API client instance."""
    global _ai_client_instance
    if _ai_client_instance is None:
        _ai_client_instance = AIAPIClient()
    return _ai_client_instance

