"""OTLP/JSON and W3C header ingestion for Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

ATTRIBUTION = "Baysöz Labs <baysozlabs@proton.me>"

_STATUS_CODES: dict[Any, str] = {
    0: "UNSET",
    1: "OK",
    2: "ERROR",
    "0": "UNSET",
    "1": "OK",
    "2": "ERROR",
    "STATUS_CODE_UNSET": "UNSET",
    "STATUS_CODE_OK": "OK",
    "STATUS_CODE_ERROR": "ERROR",
}

_KIND_CODES: dict[Any, str] = {
    0: "unspecified",
    1: "internal",
    2: "server",
    3: "client",
    4: "producer",
    5: "consumer",
    "0": "unspecified",
    "1": "internal",
    "2": "server",
    "3": "client",
    "4": "producer",
    "5": "consumer",
    "SPAN_KIND_UNSPECIFIED": "unspecified",
    "SPAN_KIND_INTERNAL": "internal",
    "SPAN_KIND_SERVER": "server",
    "SPAN_KIND_CLIENT": "client",
    "SPAN_KIND_PRODUCER": "producer",
    "SPAN_KIND_CONSUMER": "consumer",
    "unspecified": "unspecified",
    "internal": "internal",
    "server": "server",
    "client": "client",
    "producer": "producer",
    "consumer": "consumer",
}


class InputError(ValueError):
    """Raised when a document cannot be interpreted as OTLP/JSON traces."""


@dataclass(frozen=True)
class Event:
    name: str
    attributes: dict[str, Any]


@dataclass(frozen=True)
class Link:
    trace_id: str
    span_id: str
    flags: int
    flags_repr: Any
    trace_state: str


@dataclass(frozen=True)
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str
    name: str
    kind: str
    start_ns: int | None
    end_ns: int | None
    attributes: dict[str, Any]
    flags: int
    flags_repr: Any
    status_code: str
    status_message: str
    events: tuple[Event, ...]
    links: tuple[Link, ...]
    scope_name: str
    resource: dict[str, Any]
    path: str


@dataclass(frozen=True)
class ContextObservation:
    source: str
    traceparent: str
    tracestate: str
    baggage: str
    path: str


@dataclass(frozen=True)
class TraceDocument:
    spans: tuple[Span, ...]
    observations: tuple[ContextObservation, ...]


def _decode_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "intValue", "boolValue", "doubleValue", "bytesValue"):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        array = value["arrayValue"]
        if not isinstance(array, dict):
            return []
        return [_decode_value(item) for item in array.get("values", [])]
    if "kvlistValue" in value:
        kvlist = value["kvlistValue"]
        if not isinstance(kvlist, dict):
            return {}
        return decode_attributes(kvlist.get("values", []))
    return value


def decode_attributes(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): _decode_value(value) for key, value in raw.items()}
    if not isinstance(raw, list):
        return {}
    decoded: dict[str, Any] = {}
    for item in raw:
        if isinstance(item, dict) and "key" in item:
            decoded[str(item["key"])] = _decode_value(item.get("value"))
    return decoded


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value, 10)
        except ValueError:
            return None
    return None


def _as_flags(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return -1
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 16)
        except ValueError:
            return -1
    return -1


def _status(raw: Any) -> tuple[str, str]:
    if isinstance(raw, dict):
        code = raw.get("code", 0)
        message = _as_text(raw.get("message"))
    else:
        code = raw if raw is not None else 0
        message = ""
    return _STATUS_CODES.get(code, _as_text(code).upper().replace("STATUS_CODE_", "")), message


def _kind(raw: Any) -> str:
    return _KIND_CODES.get(raw, _as_text(raw).lower().replace("span_kind_", "") or "unknown")


def _events(raw: Any) -> tuple[Event, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        Event(name=_as_text(item.get("name")), attributes=decode_attributes(item.get("attributes", [])))
        for item in raw
        if isinstance(item, dict)
    )


def _links(raw: Any) -> tuple[Link, ...]:
    if not isinstance(raw, list):
        return ()
    result: list[Link] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        flags_repr = item.get("flags", item.get("traceFlags"))
        result.append(
            Link(
                trace_id=_as_text(item.get("traceId", item.get("trace_id"))),
                span_id=_as_text(item.get("spanId", item.get("span_id"))),
                flags=_as_flags(flags_repr),
                flags_repr=flags_repr,
                trace_state=_as_text(item.get("traceState", item.get("tracestate"))),
            )
        )
    return tuple(result)


def _span(raw: Any, path: str, resource: dict[str, Any], scope_name: str) -> Span | None:
    if not isinstance(raw, dict):
        return None
    status_code, status_message = _status(raw.get("status"))
    flags_repr = raw.get("flags", raw.get("traceFlags"))
    return Span(
        trace_id=_as_text(raw.get("traceId", raw.get("trace_id"))),
        span_id=_as_text(raw.get("spanId", raw.get("span_id"))),
        parent_span_id=_as_text(raw.get("parentSpanId", raw.get("parent_span_id"))),
        name=_as_text(raw.get("name")),
        kind=_kind(raw.get("kind")),
        start_ns=_as_int(raw.get("startTimeUnixNano", raw.get("start_time_unix_nano"))),
        end_ns=_as_int(raw.get("endTimeUnixNano", raw.get("end_time_unix_nano"))),
        attributes=decode_attributes(raw.get("attributes", [])),
        flags=_as_flags(flags_repr),
        flags_repr=flags_repr,
        status_code=status_code,
        status_message=status_message,
        events=_events(raw.get("events", [])),
        links=_links(raw.get("links", [])),
        scope_name=scope_name,
        resource=resource,
        path=path,
    )


def _collect_spans(document: dict[str, Any]) -> tuple[Span, ...]:
    spans: list[Span] = []
    if "resourceSpans" in document or "resource_spans" in document:
        raw_resources = document.get("resourceSpans", document.get("resource_spans", []))
        if not isinstance(raw_resources, list):
            raise InputError("resourceSpans must be an array")
        for resource_index, raw_resource in enumerate(raw_resources):
            if not isinstance(raw_resource, dict):
                continue
            resource = decode_attributes(raw_resource.get("resource", {}).get("attributes", []))
            raw_scopes = raw_resource.get("scopeSpans", raw_resource.get("instrumentationLibrarySpans", []))
            if not isinstance(raw_scopes, list):
                raise InputError("scopeSpans must be an array")
            for scope_index, raw_scope in enumerate(raw_scopes):
                if not isinstance(raw_scope, dict):
                    continue
                scope = raw_scope.get("scope", {})
                scope_name = _as_text(scope.get("name")) if isinstance(scope, dict) else ""
                raw_span_list = raw_scope.get("spans", [])
                if not isinstance(raw_span_list, list):
                    raise InputError("spans must be an array")
                for span_index, raw_span in enumerate(raw_span_list):
                    path = f"resourceSpans[{resource_index}].scopeSpans[{scope_index}].spans[{span_index}]"
                    parsed = _span(raw_span, path, resource, scope_name)
                    if parsed is not None:
                        spans.append(parsed)
    elif "spans" in document:
        raw_span_list = document["spans"]
        if not isinstance(raw_span_list, list):
            raise InputError("spans must be an array")
        for span_index, raw_span in enumerate(raw_span_list):
            parsed = _span(raw_span, f"spans[{span_index}]", {}, "")
            if parsed is not None:
                spans.append(parsed)
    else:
        raise InputError("expected 'resourceSpans' or 'spans' in the trace document")
    return tuple(spans)


def _observations(document: dict[str, Any]) -> tuple[ContextObservation, ...]:
    raw_list = document.get("contextObservations", document.get("context_observations", []))
    if not isinstance(raw_list, list):
        raise InputError("contextObservations must be an array")
    result: list[ContextObservation] = []
    for index, raw in enumerate(raw_list):
        if not isinstance(raw, dict):
            continue
        result.append(
            ContextObservation(
                source=_as_text(raw.get("source", f"observation[{index}]")),
                traceparent=_as_text(raw.get("traceparent")),
                tracestate=_as_text(raw.get("tracestate")),
                baggage=_as_text(raw.get("baggage")),
                path=f"contextObservations[{index}]",
            )
        )
    return tuple(result)


def parse_document(document: Any) -> TraceDocument:
    if isinstance(document, list):
        parsed: tuple[Span, ...] = tuple(
            span for index, raw in enumerate(document) if (span := _span(raw, f"[{index}]", {}, "")) is not None
        )
        return TraceDocument(spans=parsed, observations=())
    if not isinstance(document, dict):
        raise InputError("the trace document must be a JSON object or an array of spans")
    return TraceDocument(spans=_collect_spans(document), observations=_observations(document))
