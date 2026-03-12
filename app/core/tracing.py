from dataclasses import dataclass
from typing import Any


@dataclass
class TraceContext:
    name: str
    attributes: dict[str, Any]

    def end(self) -> None:
        return None


class TracingAdapter:
    def start_span(self, name: str, **attributes: Any) -> TraceContext:
        return TraceContext(name=name, attributes=attributes)
