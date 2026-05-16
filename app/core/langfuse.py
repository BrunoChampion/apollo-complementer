from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import Settings, get_settings


class SpanContext(Protocol):
    def __enter__(self): ...

    def __exit__(self, exc_type, exc, traceback) -> bool | None: ...

    def update(
        self,
        *,
        output: Any | None = None,
        metadata: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None: ...


class Tracer(Protocol):
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> SpanContext: ...

    def generation(
        self,
        name: str,
        *,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext: ...

    def langchain_callbacks(self) -> list[Any]: ...

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None: ...

    def flush(self) -> None: ...


class NoOpObservation:
    def __enter__(self) -> "NoOpObservation":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool | None:
        return None

    def update(
        self,
        *,
        output: Any | None = None,
        metadata: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        return None


class NoOpTracer:
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> SpanContext:
        return NoOpObservation()

    def generation(
        self,
        name: str,
        *,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        return NoOpObservation()

    def langchain_callbacks(self) -> list[Any]:
        return []

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        return None

    def flush(self) -> None:
        return None


@dataclass
class TraceRecord:
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryTracer:
    def __init__(self) -> None:
        self.spans: list[TraceRecord] = []
        self.generations: list[TraceRecord] = []
        self.scores: list[TraceRecord] = []

    @contextmanager
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> Iterator[None]:
        self.spans.append(TraceRecord(name=name, metadata=metadata or {}))
        yield

    @contextmanager
    def generation(
        self,
        name: str,
        *,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[NoOpObservation]:
        generation_metadata = dict(metadata or {})
        if model:
            generation_metadata["model"] = model
        if input is not None:
            generation_metadata["input"] = input
        self.generations.append(TraceRecord(name=name, metadata=generation_metadata))
        yield NoOpObservation()

    def langchain_callbacks(self) -> list[Any]:
        return []

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        score_metadata = dict(metadata or {})
        score_metadata["value"] = value
        self.scores.append(TraceRecord(name=name, metadata=score_metadata))

    def flush(self) -> None:
        return None


class LangfuseObservation:
    def __init__(
        self,
        client: Any,
        *,
        as_type: str,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.client = client
        self.as_type = as_type
        self.name = name
        self.model = model
        self.input = input
        self.metadata = metadata or {}
        self._context: Any | None = None
        self._observation: Any | None = None

    def __enter__(self) -> "LangfuseObservation":
        kwargs = {
            "as_type": self.as_type,
            "name": self.name,
            "metadata": self.metadata,
        }
        if self.input is not None:
            kwargs["input"] = self.input
        if self.model:
            kwargs["model"] = self.model
        try:
            self._context = self.client.start_as_current_observation(**kwargs)
        except TypeError:
            kwargs.pop("as_type", None)
            try:
                self._context = self.client.start_as_current_span(**kwargs)
            except Exception:
                self._context = nullcontext()
        except Exception:
            self._context = nullcontext()
        self._observation = self._context.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool | None:
        if self._context is None:
            return None
        return self._context.__exit__(exc_type, exc, traceback)

    def update(
        self,
        *,
        output: Any | None = None,
        metadata: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {}
        if output is not None:
            payload["output"] = output
        if metadata:
            payload["metadata"] = metadata
        if usage:
            payload["usage_details"] = usage
        if not payload:
            return

        if self._observation is not None and hasattr(self._observation, "update"):
            try:
                self._observation.update(**payload)
                return
            except TypeError:
                payload.pop("usage_details", None)
                try:
                    self._observation.update(**payload)
                    return
                except Exception:
                    pass
            except Exception:
                pass

        method_name = (
            "update_current_generation"
            if self.as_type == "generation"
            else "update_current_span"
        )
        method = getattr(self.client, method_name, None)
        if method:
            try:
                method(**payload)
            except TypeError:
                payload.pop("usage_details", None)
                try:
                    method(**payload)
                except Exception:
                    pass
            except Exception:
                pass


class LangfuseTracer:
    def __init__(self, settings: Settings) -> None:
        try:
            from langfuse import Langfuse, get_client
        except ImportError as exc:
            raise RuntimeError("langfuse package is not installed") from exc

        _configure_langfuse_environment(settings)
        self.client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            environment=settings.app_env,
            mask=mask_langfuse_data,
        )
        # Ensure integrations using the singleton client see the configured instance.
        get_client()

    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> SpanContext:
        return LangfuseObservation(
            self.client,
            as_type="span",
            name=name,
            metadata=mask_langfuse_data(metadata or {}),
        )

    def generation(
        self,
        name: str,
        *,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        return LangfuseObservation(
            self.client,
            as_type="generation",
            name=name,
            model=model,
            input=mask_langfuse_data(input),
            metadata=mask_langfuse_data(metadata or {}),
        )

    def langchain_callbacks(self) -> list[Any]:
        try:
            from langfuse.langchain import CallbackHandler
        except Exception:
            return []
        try:
            return [CallbackHandler()]
        except Exception:
            return []

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        if hasattr(self.client, "score_current_trace"):
            self.client.score_current_trace(
                name=name,
                value=value,
                metadata=mask_langfuse_data(metadata or {}),
            )

    def flush(self) -> None:
        if hasattr(self.client, "flush"):
            self.client.flush()


def get_tracer(settings: Settings | None = None) -> Tracer:
    settings = settings or get_settings()
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return NoOpTracer()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return NoOpTracer()
    try:
        return LangfuseTracer(settings)
    except Exception:
        return NoOpTracer()


SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "client_secret",
    "gmail_draft_url",
    "manual_company_linkedin_text",
    "manual_person_linkedin_text",
    "openai_api_key",
    "password",
    "prospect_email",
    "refresh_token",
    "secret",
    "token",
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LONG_TEXT_LIMIT = 700


def mask_langfuse_data(data: Any, **_: Any) -> Any:
    """Client-side masking before data leaves the application."""
    if isinstance(data, dict):
        masked: dict[str, Any] = {}
        for key, value in data.items():
            key_text = str(key).lower()
            if any(part in key_text for part in SENSITIVE_KEY_PARTS):
                masked[key] = "[REDACTED]"
            else:
                masked[key] = mask_langfuse_data(value)
        return masked
    if isinstance(data, list):
        return [mask_langfuse_data(item) for item in data]
    if isinstance(data, tuple):
        return tuple(mask_langfuse_data(item) for item in data)
    if isinstance(data, str):
        value = EMAIL_RE.sub("[REDACTED_EMAIL]", data)
        if len(value) > LONG_TEXT_LIMIT:
            return value[:LONG_TEXT_LIMIT] + "...[TRUNCATED]"
        return value
    return data


def _configure_langfuse_environment(settings: Settings) -> None:
    if settings.langfuse_public_key:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    if settings.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_host:
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
        os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_host)
