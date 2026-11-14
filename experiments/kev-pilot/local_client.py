"""Strict loopback-only Kev transport. This module executes no tools or policies."""
from __future__ import annotations

import json
import math
import os
import stat
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_PORT = 8019
PINNED_SOURCE = "2074cc44256200bb37540103fa4572901faa10f3"
PINNED_RUN = "jaredpalmer/kev-4b@139fdd94f1b6a6ad80cc15e08fcb99cac885a101"
EXPECTED_BASE = "Qwen/Qwen3.5-4B-Base"
EXPECTED_TEMPERATURE = 2.41
MAX_STATE_BYTES = 65536  # A byte bound, not an estimate of tokenizer length.
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class ClientError(ValueError):
    """Sanitized transport, admission or response-validation error."""


def _number(value, name, low=0, high=None):
    try:
        finite = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except (OverflowError, ValueError, TypeError):
        finite = False
    if not finite:
        raise ClientError(f"invalid {name}")
    if value < low or (high is not None and value > high):
        raise ClientError(f"invalid {name}")
    return value


def _json(data):
    try:
        return json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise ClientError("request is not finite JSON") from None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, token_file, base_url=None, expected_run=PINNED_RUN, timeout=30):
        base_url = base_url or f"http://127.0.0.1:{DEFAULT_PORT}"
        if base_url != f"http://127.0.0.1:{DEFAULT_PORT}":
            raise ClientError("endpoint must be the configured literal loopback address")
        _number(timeout, "timeout", 0.01, 300)
        self.base_url, self.expected_run, self.timeout = base_url, expected_run, timeout
        path = Path(token_file)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd) as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise ClientError("token file must be a private owned regular file")
                self._token = stream.read(4097).strip()
        except (OSError, UnicodeError):
            raise ClientError("cannot open private token file") from None
        if not 24 <= len(self._token) <= 4096 or not self._token.isalnum():
            raise ClientError("invalid token file")
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        self.models = None

    def _http(self, path, data=None):
        request = urllib.request.Request(
            self.base_url + path, data=None if data is None else _json(data),
            headers={"Authorization": "Bearer " + self._token, "Content-Type": "application/json"},
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ClientError(f"HTTP {response.status}")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            code = exc.code
            exc.close()
            raise ClientError(f"HTTP {code}") from None
        except (OSError, urllib.error.URLError, TimeoutError):
            raise ClientError("local request failed or timed out") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ClientError("response exceeds byte limit")
        try:
            result = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError, RecursionError):
            raise ClientError("response is not finite JSON") from None
        if not isinstance(result, dict):
            raise ClientError("response must be an object")
        return result

    def get_models(self):
        result = self._http("/v1/models")
        cards = result.get("models")
        if not isinstance(cards, list) or not cards:
            raise ClientError("missing model cards")
        for card in cards:
            if not isinstance(card, dict) or card.get("run") != self.expected_run:
                raise ClientError("loaded checkpoint mismatch")
            if card.get("backend") != "mlx" or card.get("truncate_states") is not False:
                raise ClientError("unexpected backend or truncation setting")
            if card.get("base") != EXPECTED_BASE or card.get("device") != "mps" or card.get("dtype") != "bfloat16":
                raise ClientError("unexpected base, device or precision")
            temperature = _number(card.get("temperature"), "temperature", 0.000001)
            if abs(temperature - EXPECTED_TEMPERATURE) > 0.01:
                raise ClientError("unexpected calibration temperature")
        self.models = result
        return result

    @staticmethod
    def _questions(questions):
        if not isinstance(questions, dict) or not questions or len(questions) > 64:
            raise ClientError("questions must contain 1..64 items")
        for key, question in questions.items():
            if not isinstance(key, str) or not key or not isinstance(question, dict):
                raise ClientError("invalid question")
            if set(question) - {"type", "instructions", "criteria"}:
                raise ClientError("unknown question field")
            kind, criteria = question.get("type"), question.get("criteria")
            if kind == "choice":
                if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 255 or any(not isinstance(k, str) or not k for k in criteria):
                    raise ClientError("choice requires 2..255 named options")
            elif kind == "score":
                if not isinstance(criteria, list) or not 2 <= len(criteria) <= 255:
                    raise ClientError("score requires 2..255 ordered levels")
            elif kind == "noul":
                if criteria is not None and (not isinstance(criteria, dict) or set(criteria) - {"true", "false"}):
                    raise ClientError("invalid noul criteria")
            else:
                raise ClientError("unknown question type")
        _json(questions)

    def request(self, state, questions):
        self._questions(questions)
        if len(_json(state)) > MAX_STATE_BYTES:
            raise ClientError("state exceeds byte budget; tokenizer limit must also be checked")
        if self.models is None:
            self.get_models()
        result = self._http("/v1/systemone", {"model": "kev-latest", "state": state, "questions": questions})
        if set(result) - {"model", "answers", "usage", "latency_ms", "truncated"}:
            raise ClientError("unknown response field")
        if result.get("model") != "kev-latest" or result.get("truncated", False) is not False:
            raise ClientError("unexpected response model or truncation")
        answers = result.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise ClientError("missing or unexpected answer")
        for key, question in questions.items():
            answer, kind = answers[key], question["type"]
            if not isinstance(answer, dict) or answer.get("type") != kind:
                raise ClientError("answer type mismatch")
            if kind == "noul":
                if set(answer) != {"type", "noul"}:
                    raise ClientError("unknown noul answer field")
                _number(answer.get("noul"), "noul probability", high=1)
                continue
            fields = {"type", "probabilities", "confidence", "choice"} if kind == "choice" else {"type", "probabilities", "confidence", "score", "legend"}
            if set(answer) != fields:
                raise ClientError("unexpected answer fields")
            expected = set(question["criteria"]) if kind == "choice" else {str(i) for i in range(len(question["criteria"]))}
            probabilities = answer.get("probabilities")
            if not isinstance(probabilities, dict) or set(probabilities) != expected:
                raise ClientError("probability keys mismatch")
            values = [_number(v, "probability", high=1) for v in probabilities.values()]
            if abs(sum(values) - 1) > 0.00005 * len(values) + 0.00001:
                raise ClientError("probability distribution does not sum to one")
            _number(answer.get("confidence"), "confidence", high=1)
            if kind == "choice":
                picked = answer.get("choice")
                if not isinstance(picked, str) or picked not in expected or probabilities[picked] < max(values) - 0.0001:
                    raise ClientError("invalid selected choice")
            else:
                score = _number(answer.get("score"), "score", high=len(expected) - 1)
                rounding_bound = 0.00005 * (sum(range(len(expected))) + 1) + 0.00001
                if abs(score - sum(int(k) * v for k, v in probabilities.items())) > rounding_bound:
                    raise ClientError("score does not match distribution")
                legend = answer.get("legend")
                if not isinstance(legend, dict) or set(legend) != expected or any(not isinstance(v, str) for v in legend.values()):
                    raise ClientError("invalid score legend")
        usage = result.get("usage")
        if not isinstance(usage, dict):
            raise ClientError("missing usage")
        for key in ("input_tokens", "output_tokens"):
            if type(usage.get(key)) is not int or usage[key] < 0:
                raise ClientError("invalid usage")
        if "state_tokens" in usage and usage.get("state_tokens_used") != usage["state_tokens"]:
            raise ClientError("state token count mismatch")
        _number(result.get("latency_ms"), "latency")
        return result
