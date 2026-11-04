class LLMError(Exception):
    """Base class for every LLM problem. The ticket goes to a human."""


class LLMTemporaryError(LLMError):
    """Timeout, rate limit (429) or server error. Worth retrying."""


class LLMUnavailableError(LLMError):
    """All retries failed. The LLM is not reachable right now."""


class LLMOutputError(LLMError):
    """The model answered, but the answer is empty, not JSON or off-list. Not retried."""
