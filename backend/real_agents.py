"""Adapters for testing user-owned agents over real HTTP transports."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import httpx
import neatlogs

from core.types import AgentRole, EventKind, PipelineResult, RunStatus, TraceEvent


def _event(action: str, kind: EventKind, input_data: dict[str, Any], output_data: dict[str, Any],
           metadata: dict[str, Any] | None = None, trusted: bool = True) -> TraceEvent:
    return TraceEvent(
        agent=AgentRole.REQUESTER,
        kind=kind,
        action=action,
        input_data=input_data,
        output_data=output_data,
        metadata=metadata or {},
        trusted=trusted,
        unverified_source=not trusted,
    )


def _json_or_text(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def stream_http_agent(
    *,
    name: str,
    url: str,
    method: str,
    headers: dict[str, str],
    payload: Any,
    timeout_seconds: float,
) -> Iterator[dict[str, Any]]:
    """Send one real request and yield facts as they happen.

    The final result is completed only after an actual HTTP response is
    received. A connection failure is explicitly failed and never presented
    as a tested agent.
    """
    result = PipelineResult(
        scenario_name=name,
        status=RunStatus.RUNNING,
        started_at=datetime.utcnow().isoformat(),
    )
    started = time.perf_counter()
    safe_headers = {key: value for key, value in headers.items() if key.lower() not in {"authorization", "x-api-key"}}

    result.trace.append(_event(
        "real_agent_request",
        EventKind.TOOL_CALL,
        {"method": method, "url": url, "headers": safe_headers, "payload": payload},
        {},
        {"transport": "http", "request_sent": False},
    ))
    neatlogs.log("real agent request sent to {url}", level="info", url=url, transport="http")
    yield {"type": "event", "event": result.trace[-1], "phase": "request"}
    yield {"type": "phase", "phase": "request", "message": "Sending a real request to the configured agent…"}

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.request(method.upper(), url, headers=headers, json=payload)
        response_body = _json_or_text(response)
        received_at = datetime.utcnow().isoformat()
        result.trace.append(_event(
            "real_agent_response",
            EventKind.TOOL_RESULT,
            {"status_code": response.status_code, "content_type": response.headers.get("content-type", "")},
            {"body": response_body},
            {
                "transport": "http",
                "request_sent": True,
                "response_received": True,
                "response_bytes": len(response.content),
                "received_at": received_at,
            },
            trusted=False,
        ))
        neatlogs.log(
            "real agent response received with HTTP {status_code}",
            level="info" if response.is_success else "warning",
            status_code=response.status_code,
            response_bytes=len(response.content),
        )
        yield {"type": "event", "event": result.trace[-1], "phase": "response"}
        result.status = RunStatus.COMPLETED if 200 <= response.status_code < 400 else RunStatus.FAILED
        if result.status == RunStatus.FAILED:
            result.error = f"Agent returned HTTP {response.status_code}"
        yield {
            "type": "phase",
            "phase": "response",
            "message": f"Received a real HTTP response ({response.status_code}).",
        }
    except (httpx.HTTPError, ValueError) as exc:
        result.status = RunStatus.FAILED
        result.error = f"{type(exc).__name__}: {exc}"
        result.trace.append(_event(
            "real_agent_transport_error",
            EventKind.ERROR,
            {"url": url, "method": method},
            {"error": result.error},
            {"transport": "http", "request_sent": True, "response_received": False},
            trusted=True,
        ))
        neatlogs.log("real agent request failed: {error}", level="error", error=result.error)
        yield {"type": "event", "event": result.trace[-1], "phase": "error"}
        yield {"type": "phase", "phase": "error", "message": "The real request failed; no agent test result is claimed."}

    result.latency_ms = int((time.perf_counter() - started) * 1000)
    result.finished_at = datetime.utcnow().isoformat()
    result.defenses = []
    yield {"type": "result", "result": result}


def openai_payload(model: str, prompt: str, system_prompt: str, temperature: float) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return {"model": model, "messages": messages, "temperature": temperature}


def parse_json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed
