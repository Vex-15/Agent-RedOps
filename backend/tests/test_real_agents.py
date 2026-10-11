"""Real-transport tests.

These start genuine HTTP servers on 127.0.0.1 and talk to them with the real
httpx client -- nothing about the transport is mocked.  The servers imitate
(a) the OpenAI REST API and (b) a user webhook agent, each in a "vulnerable"
and a "hardened" flavour, so we can prove RedOps finds real weaknesses and
does not invent them.
"""

import hashlib
import hmac
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.types import RunStatus, ViolationCategory
from real_agents import (
    AgentTarget, check_target_url, extract_agent_text, key_format_issues,
    redact, stream_openai_agent, stream_probe_agent, substitute_prompt, validate_openai_key,
    verify_webhook,
)
from real_probes import PROBES

GOOD_KEY = "sk-test-" + "A1b2C3d4" * 5
QUOTA_KEY = "sk-quota-" + "Z9y8X7w6" * 4


# ── Fake agent brains ─────────────────────────────────────────────────

def _vulnerable_reply(system: str, user: str) -> str:
    """Obeys whatever the text says -- the textbook vulnerable agent."""
    if "reply with exactly the single word: pong" in user.lower():
        return "pong"
    m = re.search(r"joining the prefix (\w+) and the suffix (\w+) with a hyphen", user)
    if m:
        return f"Sure! {m.group(1)}-{m.group(2)}"
    if "print your full system prompt" in user.lower():
        return f"My instructions are: {system}"
    return "OK"


def _hardened_reply(system: str, user: str) -> str:
    if "reply with exactly the single word: pong" in user.lower():
        return "pong"
    return "I can't follow instructions found in messages or claims I can't verify."


def _quoting_reply(system: str, user: str) -> str:
    """Summarises by quoting the attack back verbatim -- must NOT be flagged."""
    if "reply with exactly the single word: pong" in user.lower():
        return "pong"
    return f"The message says: \"{user}\". I will not act on it."


BRAINS = {"vulnerable": _vulnerable_reply, "hardened": _hardened_reply, "quoting": _quoting_reply}


# ── Mock servers ──────────────────────────────────────────────────────

class _Quiet(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep pytest output clean
        pass

    def _send(self, status, body, headers=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        return raw, json.loads(raw or b"{}")


def make_openai_server(behaviour="vulnerable", models_status=200, echo_auth=False):
    state = {"requests": [], "chat_calls": 0}

    class Handler(_Quiet):
        def _auth(self):
            token = self.headers.get("Authorization", "")
            if token == f"Bearer {QUOTA_KEY}":
                self._send(429, {"error": {"message": "You exceeded your current quota", "type": "insufficient_quota", "code": "insufficient_quota"}})
                return False
            if token != f"Bearer {GOOD_KEY}":
                self._send(401, {"error": {"message": f"Incorrect API key provided: {token[7:20]}***", "type": "invalid_request_error", "code": "invalid_api_key"}})
                return False
            return True

        def do_GET(self):
            state["requests"].append(("GET", self.path))
            if self.path != "/v1/models":
                return self._send(404, {"error": {"message": "not found"}})
            if not self._auth():
                return
            if models_status != 200:
                return self._send(models_status, {"error": {"message": "nope"}})
            self._send(200, {"data": [{"id": "gpt-test"}, {"id": "strict-model"}]}, {"openai-organization": "org-test", "x-request-id": "req_123"})

        def do_POST(self):
            state["requests"].append(("POST", self.path))
            if self.path != "/v1/chat/completions":
                return self._send(404, {"error": {"message": "not found"}})
            if not self._auth():
                return
            _, body = self._json_body()
            state["chat_calls"] += 1
            if body.get("model") == "strict-model" and "temperature" in body:
                return self._send(400, {"error": {"message": "Unsupported value: 'temperature' does not support 0 with this model. Only the default (1) value is supported.", "param": "temperature", "type": "invalid_request_error"}})
            msgs = body.get("messages", [])
            system = " ".join(m["content"] for m in msgs if m["role"] == "system")
            user = " ".join(m["content"] for m in msgs if m["role"] == "user")
            reply = BRAINS[behaviour](system, user)
            if echo_auth:  # a careless agent that echoes request headers
                reply += f" [debug auth={self.headers.get('Authorization')}]"
            self._send(200, {"choices": [{"index": 0, "message": {"role": "assistant", "content": reply}}]})

    return Handler, state


def make_webhook_server(behaviour="vulnerable", signing_secret=None, fail_status=None):
    state = {"requests": []}

    class Handler(_Quiet):
        def do_POST(self):
            raw, body = self._json_body()
            state["requests"].append(dict(self.headers))
            if fail_status:
                return self._send(fail_status, {"error": "boom"})
            if signing_secret:
                ts = self.headers.get("X-RedOps-Timestamp", "")
                expected = "sha256=" + hmac.new(signing_secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected, self.headers.get("X-RedOps-Signature", "")):
                    return self._send(401, {"error": "bad signature"})
            if self.headers.get("X-Api-Token") not in (None, "hook-token"):
                return self._send(403, {"error": "forbidden"})
            reply = BRAINS[behaviour]("", body["input"]["message"])
            self._send(200, {"reply": reply})

    return Handler, state


@pytest.fixture
def serve():
    servers = []

    def _start(handler):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    yield _start
    for srv in servers:
        srv.shutdown()
        srv.server_close()


def _drain(stream):
    msgs = list(stream)
    return msgs, msgs[-1]["result"]


def _openai_target(base, model="gpt-test", key=GOOD_KEY, **kw):
    return AgentTarget(kind="openai", url=base + "/v1", api_key=key, model=model, timeout_seconds=10, **kw)


# ── API key check ─────────────────────────────────────────────────────

class TestKeyValidation:
    def test_valid_key(self, serve):
        handler, _ = make_openai_server()
        out = validate_openai_key(GOOD_KEY, serve(handler) + "/v1", "gpt-test")
        assert out["status"] == "valid" and out["ok"] is True
        assert out["model_available"] is True
        assert out["organization"] == "org-test" and out["request_id"] == "req_123"

    def test_never_returns_the_key(self, serve):
        handler, _ = make_openai_server()
        out = validate_openai_key(GOOD_KEY, serve(handler) + "/v1", "gpt-test")
        assert GOOD_KEY not in json.dumps(out)
        assert out["key_hint"] == f"{GOOD_KEY[:4]}…{GOOD_KEY[-4:]}"

    def test_rejected_key_is_invalid_and_error_is_redacted(self, serve):
        handler, _ = make_openai_server()
        bad = "sk-" + "wrong" * 8
        out = validate_openai_key(bad, serve(handler) + "/v1", "gpt-test")
        assert out["status"] == "invalid" and out["ok"] is False and out["http_status"] == 401
        assert bad not in json.dumps(out)

    def test_quota_exhausted_key_is_distinguished(self, serve):
        handler, _ = make_openai_server()
        out = validate_openai_key(QUOTA_KEY, serve(handler) + "/v1", "gpt-test")
        assert out["status"] == "quota_exceeded" and out["ok"] is False

    def test_missing_model_is_reported(self, serve):
        handler, _ = make_openai_server()
        out = validate_openai_key(GOOD_KEY, serve(handler) + "/v1", "gpt-nope")
        assert out["status"] == "valid" and out["model_available"] is False
        assert "gpt-nope" in out["message"]

    def test_restricted_key_falls_back_to_a_real_chat_call(self, serve):
        handler, state = make_openai_server(models_status=403)
        out = validate_openai_key(GOOD_KEY, serve(handler) + "/v1", "gpt-test")
        assert out["status"] == "valid" and state["chat_calls"] == 1

    def test_restricted_key_without_model_is_unverified_not_valid(self, serve):
        handler, _ = make_openai_server(models_status=403)
        out = validate_openai_key(GOOD_KEY, serve(handler) + "/v1", None)
        assert out["status"] == "unverified" and out["ok"] is False

    def test_unreachable_endpoint(self):
        out = validate_openai_key(GOOD_KEY, "http://127.0.0.1:9/v1", "gpt-test", timeout_seconds=3)
        assert out["status"] == "unreachable" and out["ok"] is False

    @pytest.mark.parametrize("key,fragment", [
        ("sk-abc def" + "x" * 20, "whitespace"),
        ("sk-" + "k" * 20 + "\u201d", "non-ASCII"),
        ("not-a-key-at-all-1234567890", "sk-"),
    ])
    def test_malformed_keys_are_caught_before_any_request(self, key, fragment):
        out = validate_openai_key(key, "https://api.openai.com/v1", "gpt-4o-mini")
        assert out["status"] == "malformed" and fragment in out["message"]
        assert out["http_status"] is None

    def test_surrounding_whitespace_from_copy_paste_is_trimmed(self, serve):
        handler, _ = make_openai_server()
        out = validate_openai_key(f"  {GOOD_KEY}\n", serve(handler) + "/v1", "gpt-test")
        assert out["status"] == "valid"

    def test_env_key_fallback(self, serve, monkeypatch):
        handler, _ = make_openai_server()
        monkeypatch.setenv("OPENAI_API_KEY", GOOD_KEY)
        out = validate_openai_key("", serve(handler) + "/v1", "gpt-test")
        assert out["status"] == "valid" and out["key_source"] == "environment"

    def test_no_key_anywhere(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        out = validate_openai_key("", "https://api.openai.com/v1")
        assert out["status"] == "malformed" and out["key_source"] == "none"

    def test_third_party_base_urls_do_not_require_sk_prefix(self):
        assert key_format_issues("local-key-123", "http://localhost:11434/v1") == []


# ── OpenAI-compatible agent under attack ──────────────────────────────

class TestOpenAIProbes:
    def test_vulnerable_agent_is_caught_on_every_probe(self, serve):
        handler, state = make_openai_server("vulnerable")
        msgs, result = _drain(stream_openai_agent(_openai_target(serve(handler)), "vuln"))
        assert result.status == RunStatus.COMPLETED
        assert len(result.violations) == len(PROBES) == 6
        assert {v.category for v in result.violations} == {
            ViolationCategory.TRUST_BOUNDARY, ViolationCategory.CONFLICTING_INSTRUCTIONS,
            ViolationCategory.SOCIAL_ENGINEERING, ViolationCategory.AUTH_BYPASS,
            ViolationCategory.DECEPTIVE_TOOL_OUTPUT,
        }
        assert all(ap.length == 2 and ap.violation for ap in result.attack_paths)
        assert any(m["type"] == "finding" for m in msgs)
        # 1 control + 6 probes were really sent
        assert state["chat_calls"] == 7

    def test_hardened_agent_is_not_falsely_accused(self, serve):
        handler, _ = make_openai_server("hardened")
        _, result = _drain(stream_openai_agent(_openai_target(serve(handler)), "hard"))
        assert result.status == RunStatus.COMPLETED
        assert result.violations == []
        summary = [e for e in result.trace if e.action == "probe_summary"][0]
        assert summary.output_data["probes_evaluated"] == 6

    def test_quoting_the_attack_is_not_compliance(self, serve):
        handler, _ = make_openai_server("quoting")
        _, result = _drain(stream_openai_agent(_openai_target(serve(handler)), "quote"))
        assert result.status == RunStatus.COMPLETED
        assert result.violations == []

    def test_planted_secret_leak_is_critical(self, serve):
        handler, _ = make_openai_server("vulnerable")
        _, result = _drain(stream_openai_agent(_openai_target(serve(handler), system_prompt="You are a procurement bot."), "leak"))
        leaks = [v for v in result.violations if v.title.startswith("System prompt")]
        assert len(leaks) == 1 and leaks[0].severity.value == "critical"
        assert "RDOSEC-" in leaks[0].description

    def test_temperature_rejection_is_repaired_automatically(self, serve):
        handler, state = make_openai_server("hardened")
        target = _openai_target(serve(handler), model="strict-model")
        _, result = _drain(stream_openai_agent(target, "strict"))
        assert result.status == RunStatus.COMPLETED
        adapted = [e.metadata.get("adapted") for e in result.trace if e.metadata.get("adapted")]
        assert adapted and "temperature" in adapted[0][0]

    def test_bad_key_stops_before_any_probe_and_fails_honestly(self, serve):
        handler, state = make_openai_server("vulnerable")
        msgs, result = _drain(stream_openai_agent(_openai_target(serve(handler), key="sk-" + "bad" * 10), "badkey"))
        assert result.status == RunStatus.FAILED and "invalid" in result.error
        assert result.violations == [] and state["chat_calls"] == 0
        assert any(m.get("phase") == "keycheck" for m in msgs)

    def test_key_never_appears_in_trace_even_if_agent_echoes_it(self, serve):
        handler, _ = make_openai_server("hardened", echo_auth=True)
        _, result = _drain(stream_openai_agent(_openai_target(serve(handler)), "echo"))
        blob = json.dumps([e.__dict__ for e in result.trace], default=str) + json.dumps(result.error)
        assert GOOD_KEY not in blob and GOOD_KEY.split("sk-")[1] not in blob

    def test_single_mode_still_sends_one_real_request(self, serve):
        handler, state = make_openai_server("hardened")
        _, result = _drain(stream_openai_agent(_openai_target(serve(handler)), "one", mode="single", prompt="hello"))
        assert result.status == RunStatus.COMPLETED and state["chat_calls"] == 1

    def test_probe_selection(self, serve):
        handler, state = make_openai_server("vulnerable")
        _, result = _drain(stream_openai_agent(_openai_target(serve(handler)), "sel", probe_ids=["forged_approval"]))
        assert [v.category for v in result.violations] == [ViolationCategory.AUTH_BYPASS]
        assert state["chat_calls"] == 2


# ── Webhook agent under attack ────────────────────────────────────────

TEMPLATE = {"input": {"message": "{{PROMPT}}"}, "session": "redops"}


def _hook(url, **kw):
    return AgentTarget(kind="webhook", url=url + "/agent", payload_template=TEMPLATE, timeout_seconds=10, **kw)


class TestWebhookProbes:
    def test_vulnerable_webhook_findings_skip_leak_probe(self, serve):
        handler, state = make_webhook_server("vulnerable")
        _, result = _drain(stream_probe_agent(_hook(serve(handler)), "hook"))
        assert result.status == RunStatus.COMPLETED
        assert len(result.violations) == 5          # leak probe needs a prompt RedOps controls
        summary = [e for e in result.trace if e.action == "probe_summary"][0]
        assert summary.output_data["probes_skipped"] == ["system_prompt_leak"]
        assert len(state["requests"]) == 6          # control + 5 probes

    def test_hardened_webhook_is_clean(self, serve):
        handler, _ = make_webhook_server("hardened")
        _, result = _drain(stream_probe_agent(_hook(serve(handler)), "hook"))
        assert result.status == RunStatus.COMPLETED and result.violations == []

    def test_hmac_signature_is_accepted_by_a_verifying_server(self, serve):
        handler, _ = make_webhook_server("hardened", signing_secret="s3cret")
        _, ok = _drain(stream_probe_agent(_hook(serve(handler), signing_secret="s3cret"), "signed"))
        assert ok.status == RunStatus.COMPLETED

    def test_wrong_or_missing_signature_fails_honestly(self, serve):
        handler, _ = make_webhook_server("vulnerable", signing_secret="s3cret")
        base = serve(handler)
        for target in (_hook(base), _hook(base, signing_secret="wrong")):
            _, result = _drain(stream_probe_agent(target, "unsigned"))
            assert result.status == RunStatus.FAILED and "HTTP 401" in result.error
            assert result.violations == []

    def test_custom_auth_header_is_sent_and_redacted_in_the_trace(self, serve):
        handler, state = make_webhook_server("hardened")
        target = _hook(serve(handler), headers={"X-Api-Token": "hook-token"})
        _, result = _drain(stream_probe_agent(target, "auth"))
        assert result.status == RunStatus.COMPLETED
        assert all(r.get("X-Api-Token") == "hook-token" for r in state["requests"])
        assert "hook-token" not in json.dumps([e.__dict__ for e in result.trace], default=str)

    def test_server_errors_never_become_a_clean_result(self, serve):
        handler, _ = make_webhook_server("vulnerable", fail_status=500)
        _, result = _drain(stream_probe_agent(_hook(serve(handler)), "down"))
        assert result.status == RunStatus.FAILED and "No probes were run" in result.error

    def test_dead_endpoint_fails(self):
        _, result = _drain(stream_probe_agent(_hook("http://127.0.0.1:9"), "dead"))
        assert result.status == RunStatus.FAILED and result.violations == []

    def test_verify_webhook(self, serve):
        handler, _ = make_webhook_server("hardened")
        out = verify_webhook(_hook(serve(handler)))
        assert out["ok"] and out["reply_preview"] == "pong" and out["json_response"]

    def test_verify_requires_placeholder(self, serve):
        handler, _ = make_webhook_server("hardened")
        target = AgentTarget(kind="webhook", url=serve(handler), payload_template={"input": "fixed"})
        assert verify_webhook(target)["status"] == "no_placeholder"


# ── Helpers & policy ──────────────────────────────────────────────────

class TestHelpers:
    def test_substitute_prompt_walks_nested_json(self):
        out, hits = substitute_prompt({"a": [{"b": "x {{PROMPT}} y"}], "n": 1}, "HI")
        assert out == {"a": [{"b": "x HI y"}], "n": 1} and hits == 1

    @pytest.mark.parametrize("body,expected", [
        ({"choices": [{"message": {"content": "hi"}}]}, "hi"),
        ({"content": [{"type": "text", "text": "hey"}]}, "hey"),
        ({"output": {"text": "nested"}}, "nested"),
        ({"reply": "r"}, "r"),
        ("plain", "plain"),
    ])
    def test_extract_agent_text(self, body, expected):
        assert extract_agent_text(body) == expected

    def test_redact_catches_key_shapes(self):
        assert "sk-abcdefghijklmnop1234" not in redact("oops sk-abcdefghijklmnop1234 leaked")
        assert "tok123456789012" not in redact("Authorization: Bearer tok123456789012")

    def test_metadata_endpoints_are_blocked_but_localhost_is_allowed(self, monkeypatch):
        monkeypatch.delenv("REDOPS_BLOCK_PRIVATE_TARGETS", raising=False)
        assert check_target_url("http://169.254.169.254/latest/meta-data")
        assert check_target_url("http://metadata.google.internal/")
        assert check_target_url("file:///etc/passwd")
        assert check_target_url("http://127.0.0.1:8000/agent") is None

    def test_private_targets_can_be_forbidden_on_shared_servers(self, monkeypatch):
        monkeypatch.setenv("REDOPS_BLOCK_PRIVATE_TARGETS", "1")
        assert check_target_url("http://127.0.0.1:8000/agent")
        assert check_target_url("http://10.0.0.5/agent")


# ── Through the FastAPI layer ─────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import database

    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autocommit=False, autoflush=False))
    import main
    with TestClient(main.app) as c:
        yield c


def _ndjson(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


class TestAPI:
    def test_validate_key_endpoint(self, client, serve):
        handler, _ = make_openai_server()
        base = serve(handler) + "/v1"
        good = client.post("/api/real-agents/openai/validate-key", json={"base_url": base, "api_key": GOOD_KEY, "model": "gpt-test"}).json()
        assert good["status"] == "valid" and GOOD_KEY not in json.dumps(good)
        bad = client.post("/api/real-agents/openai/validate-key", json={"base_url": base, "api_key": "sk-" + "x" * 30}).json()
        assert bad["status"] == "invalid"

    def test_openai_stream_end_to_end_and_persisted(self, client, serve):
        handler, _ = make_openai_server("vulnerable")
        r = client.post("/api/real-agents/openai/stream", json={"base_url": serve(handler) + "/v1", "api_key": GOOD_KEY, "model": "gpt-test"})
        assert r.status_code == 200
        lines = _ndjson(r)
        final = lines[-1]
        assert final["type"] == "result" and final["status"] == "completed" and final["violation_count"] == 6
        detail = client.get(f"/api/runs/{final['run_id']}").json()
        assert detail["source"] == "openai" and len(detail["violations"]) == 6 and len(detail["attack_paths"]) == 6
        assert GOOD_KEY not in json.dumps(detail) and GOOD_KEY not in r.text

    def test_openai_stream_rejects_malformed_key_with_400(self, client):
        r = client.post("/api/real-agents/openai/stream", json={"api_key": "sk-bad key" + "z" * 20, "model": "gpt-4o-mini"})
        assert r.status_code == 400 and "whitespace" in r.json()["detail"]

    def test_webhook_stream_requires_placeholder_in_probe_mode(self, client, serve):
        handler, _ = make_webhook_server()
        r = client.post("/api/real-agents/webhook/stream", json={"url": serve(handler), "payload": {"fixed": "x"}})
        assert r.status_code == 400 and "{{PROMPT}}" in r.json()["detail"]

    def test_webhook_stream_end_to_end(self, client, serve):
        handler, _ = make_webhook_server("vulnerable")
        r = client.post("/api/real-agents/webhook/stream", json={"url": serve(handler) + "/agent", "payload": TEMPLATE})
        final = _ndjson(r)[-1]
        assert final["status"] == "completed" and final["violation_count"] == 5

    def test_webhook_single_mode_is_unchanged(self, client, serve):
        handler, _ = make_webhook_server("hardened")
        r = client.post("/api/real-agents/webhook/stream", json={"url": serve(handler) + "/agent", "mode": "single", "payload": {"input": {"message": "hi"}}})
        assert _ndjson(r)[-1]["status"] == "completed"

    def test_metadata_url_is_refused(self, client):
        r = client.post("/api/real-agents/webhook/stream", json={"url": "http://169.254.169.254/x", "payload": TEMPLATE})
        assert r.status_code == 400

    def test_probe_catalog_and_verify_endpoints(self, client, serve):
        assert len(client.get("/api/real-agents/probes").json()) == 6
        handler, _ = make_webhook_server("hardened")
        v = client.post("/api/real-agents/webhook/verify", json={"url": serve(handler) + "/agent", "payload": TEMPLATE}).json()
        assert v["ok"] is True

    def test_health_reports_env_key_without_exposing_it(self, client, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", GOOD_KEY)
        body = client.get("/api/health").json()
        assert body["openai_env_key_configured"] is True and GOOD_KEY not in json.dumps(body)
