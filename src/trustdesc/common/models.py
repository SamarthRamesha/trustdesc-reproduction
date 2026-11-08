"""Provider boundary: all semantic stages use the same JSON protocol.

No automatic credentials, retries, external calls or model downloads. Replays are
test doubles, not model inference. Full request/response audit stays local.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import ipaddress
import json
import socket
import time
from typing import Protocol
import urllib.error
import urllib.parse
import urllib.request

from .io import ValidationError, canonical, digest, nonempty


class ModelError(RuntimeError):
    pass


class Model(Protocol):
    model_id: str
    mode: str

    def complete(self, stage: str, system: str, payload: dict) -> dict: ...


@dataclass
class ReplayModel:
    responses: list[dict]
    model_id: str = "synthetic-replay-v1"
    mode: str = "synthetic_replay"
    audit: list = field(default_factory=list)

    def __post_init__(self):
        self._queue = deque(self.responses)

    def complete(self, stage, system, payload):
        if not self._queue:
            raise ModelError(f"Replay exhausted at {stage}")
        record = self._queue.popleft()
        if record.get("stage") != stage:
            raise ModelError(f"Replay stage mismatch: expected {stage}")
        if "request_hash" in record and record["request_hash"] != digest({"system": system, "payload": payload}):
            raise ModelError("Replay request hash mismatch")
        result = record.get("response")
        if not isinstance(result, dict):
            raise ValidationError("Replay response must be an object")
        self.audit.append({"stage": stage, "system": system, "payload": payload,
                           "request_hash": digest({"system": system, "payload": payload}),
                           "response": result, "model": self.model_id, "mode": self.mode,
                           "cost_usd": None, "tokens": None})
        return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ModelError("Model endpoint redirects are disabled")


class HTTPModel:
    """OpenRouter-compatible chat JSON interface; not exercised with paid models.

    Loopback is opt-in by constructing this provider. Remote use requires both
    permissions and an explicitly supplied key. A key is never sent to loopback
    or a plain-HTTP remote host; redirects and environment proxies are disabled.
    """

    mode = "http_inference"

    def __init__(self, endpoint: str, model_id: str, *, api_key: str | None = None,
                 allow_remote=False, allow_paid=False, timeout=30.0,
                 temperature=0.2, max_tokens=4096):
        u = urllib.parse.urlparse(endpoint)
        if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ModelError("Invalid model endpoint")
        try:
            loopback = ipaddress.ip_address(u.hostname).is_loopback
        except ValueError:
            loopback = False  # require literal loopback; no DNS ambiguity
        if not loopback:
            if not allow_remote or not allow_paid:
                raise ModelError("Remote and potentially paid model use require explicit authorization")
            if u.scheme != "https" or not api_key:
                raise ModelError("Remote provider requires HTTPS and an explicitly supplied API key")
        elif api_key:
            raise ModelError("Do not send API credentials to loopback")
        if timeout <= 0 or timeout > 120 or type(max_tokens) is not int or not 1 <= max_tokens <= 32768:
            raise ModelError("Invalid request bounds")
        self.endpoint, self.model_id, self.api_key = endpoint, nonempty(model_id, "model_id"), api_key
        self.timeout, self.temperature, self.max_tokens = timeout, temperature, max_tokens
        self.audit = []
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def complete(self, stage, system, payload):
        request = {"model": self.model_id, "temperature": self.temperature,
                   "max_tokens": self.max_tokens,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": canonical(payload)}]}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        start = time.perf_counter()
        audit = {"stage":stage,"request":request,"request_hash":digest(request),"model":self.model_id,
                 "mode":self.mode,"status":"started","cost_usd":None}
        self.audit.append(audit)
        def safe_text(text):
            return text.replace(self.api_key,'[REDACTED]') if self.api_key else text
        def safe_value(value):
            if isinstance(value,str):return safe_text(value)
            if isinstance(value,list):return [safe_value(v) for v in value]
            if isinstance(value,dict):return {safe_text(k) if isinstance(k,str) else k:safe_value(v) for k,v in value.items()}
            return value
        audit['request']=safe_value(request)
        try:
            req = urllib.request.Request(self.endpoint, data=canonical(request).encode(), headers=headers, method="POST")
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ModelError("Model response exceeds size limit")
            audit['raw_http_body'] = safe_text(raw.decode('utf-8',errors='replace'))
            envelope = json.loads(raw)
            audit.update(usage=envelope.get('usage'),resolved_model=envelope.get('model'))
            choice = envelope["choices"][0]
            if choice.get("finish_reason") not in {"stop", None}:
                raise ModelError("Incomplete model response")
            content = choice["message"]["content"]
            audit['raw_content'] = safe_text(content)
            audit.pop('raw_http_body',None)
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValidationError("Model must return a JSON object")
        except (TimeoutError, socket.timeout) as exc:
            audit.update(status='failed',error_type=type(exc).__name__)
            raise ModelError("Model timeout; no retry performed") from exc
        except (urllib.error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            audit.update(status='failed',error_type=type(exc).__name__)
            # Error bodies/credentials are deliberately not echoed.
            raise ModelError(f"Invalid or failed model response ({type(exc).__name__})") from exc
        except Exception as exc:
            audit.update(status='failed',error_type=type(exc).__name__)
            raise
        finally:
            audit['seconds']=time.perf_counter()-start
        audit.update(response=safe_value(result),status='completed')
        return result
