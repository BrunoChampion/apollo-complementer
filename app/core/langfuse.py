from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import Settings, get_settings


class SpanContext(Protocol):
    def __enter__(self): ...

    def __exit__(self, exc_type, exc, traceback) -> bool | None: ...


class Tracer(Protocol):
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> SpanContext: ...

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None: ...


class NoOpTracer:
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> SpanContext:
        return nullcontext()

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        return None


@dataclass
class TraceRecord:
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryTracer:
    def __init__(self) -> None:
        self.spans: list[TraceRecord] = []
        self.scores: list[TraceRecord] = []

    @contextmanager
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> Iterator[None]:
        self.spans.append(TraceRecord(name=name, metadata=metadata or {}))
        yield

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        score_metadata = dict(metadata or {})
        score_metadata["value"] = value
        self.scores.append(TraceRecord(name=name, metadata=score_metadata))


class LangfuseTracer:
    def __init__(self, settings: Settings) -> None:
        try:
            from langfuse import Langfuse
        except ImportError as exc:
            raise RuntimeError("langfuse package is not installed") from exc

        self.client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> SpanContext:
        if hasattr(self.client, "start_as_current_span"):
            return self.client.start_as_current_span(name=name, metadata=metadata or {})
        return nullcontext()

    def score(self, *, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        if hasattr(self.client, "score_current_trace"):
            self.client.score_current_trace(name=name, value=value, metadata=metadata or {})


def get_tracer(settings: Settings | None = None) -> Tracer:
    settings = settings or get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return NoOpTracer()
    try:
        return LangfuseTracer(settings)
    except Exception:
        return NoOpTracer()
