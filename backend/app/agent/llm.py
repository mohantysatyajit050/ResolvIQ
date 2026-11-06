import groq
from groq import Groq

from app.agent.errors import LLMError, LLMOutputError, LLMTemporaryError
from app.core.config import settings


def _error_code(exc: groq.APIStatusError) -> str | None:
    body = exc.body
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            code = error.get("code")
            return code if isinstance(code, str) else None
    return None


class GroqLLMClient:
    """Calls Groq and returns the raw JSON text. It does not parse anything."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        # max_retries=0: our own retry loop in the router decides when to retry
        self._client = Groq(api_key=api_key, timeout=timeout, max_retries=0)
        self._model = model
        self._max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        effort = (
            reasoning_effort if reasoning_effort is not None else settings.llm_reasoning_effort
        )
        effort = effort.strip().lower()
        # "off" (or empty) means: do not send the setting, for models that do not support it
        self._reasoning_effort = None if effort in ("", "off", "none") else effort

    def complete_json(self, system: str, user: str) -> str:
        extra: dict = {}
        if self._reasoning_effort:
            extra["extra_body"] = {"reasoning_effort": self._reasoning_effort}
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=self._max_tokens,
                **extra,
            )
        except (
            groq.APIConnectionError,  # also covers timeouts
            groq.RateLimitError,
            groq.InternalServerError,
        ) as exc:
            raise LLMTemporaryError(f"Temporary Groq error: {exc}") from exc
        except groq.APIStatusError as exc:
            if exc.status_code == 400 and _error_code(exc) == "json_validate_failed":
                # The model's answer was not valid JSON (for example it ran out of tokens)
                raise LLMOutputError("The model did not produce valid JSON") from exc
            # 400, 401, 403, 404 and similar: retrying will not help
            raise LLMError(f"Groq rejected the request ({exc.status_code})") from exc

        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise LLMOutputError("The model's answer was cut off (max_tokens too low)")
        content = choice.message.content
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
