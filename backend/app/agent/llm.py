import groq
from groq import Groq

from app.agent.errors import LLMError, LLMOutputError, LLMTemporaryError
from app.core.config import settings


class GroqLLMClient:
    """Calls Groq and returns the raw JSON text. It does not parse anything."""

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        # max_retries=0: our own retry loop in the router decides when to retry
        self._client = Groq(api_key=api_key, timeout=timeout, max_retries=0)
        self._model = model

    def complete_json(self, system: str, user: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=300,
            )
        except (
            groq.APIConnectionError,  # also covers timeouts
            groq.RateLimitError,
            groq.InternalServerError,
        ) as exc:
            raise LLMTemporaryError(f"Temporary Groq error: {exc}") from exc
        except groq.APIStatusError as exc:
            # 400, 401, 403, 404 and similar: retrying will not help
            raise LLMError(f"Groq rejected the request ({exc.status_code})") from exc

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise LLMOutputError("The model returned an empty answer")
        return content


class FakeLLMClient:
    """For tests. Give it answers (text) or errors (exceptions), used one by one."""

    def __init__(self, replies: list[str | Exception]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if not self._replies:
            raise AssertionError("FakeLLMClient has no more replies")
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def get_llm_client() -> GroqLLMClient:
    if settings.llm_provider != "groq":
        raise LLMError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not set in backend/.env")
    return GroqLLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
    )
