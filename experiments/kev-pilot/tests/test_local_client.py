"""Boundary tests use an ephemeral fake server, never the actual model."""
import copy
import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_client as lc
import runtime

QUESTIONS = {
    "route": {"type": "choice", "criteria": {"a": "first", "b": "second"}},
    "relevant": {"type": "noul"},
    "level": {"type": "score", "criteria": ["low", "high"]},
}
RESPONSE = {
    "model": "kev-latest", "latency_ms": 12.5,
    "usage": {"input_tokens": 30, "output_tokens": 10},
    "answers": {
        "route": {"type": "choice", "choice": "a", "probabilities": {"a": .8, "b": .2}, "confidence": .6},
        "relevant": {"type": "noul", "noul": .8},
        "level": {"type": "score", "score": .8, "probabilities": {"0": .2, "1": .8}, "confidence": .6, "legend": {"0": "low", "1": "high"}},
    },
}


class TestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send(cls.test.models)

            def do_POST(self):
                cls.test.calls += 1
                cls.test.sent = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                cls.test.authorization = self.headers.get("Authorization")
                self.send(cls.test.response)

            def send(self, value):
                if cls.test.redirect:
                    self.send_response(302)
                    self.send_header("Location", "http://198.51.100.1:9999/exfiltrate")
                    self.end_headers()
                    return
                time.sleep(cls.test.delay)
                self.send_response(cls.test.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                try:
                    self.wfile.write(value if isinstance(value, bytes) else json.dumps(value).encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        type(self).test = self
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.token = Path(self.temp.name) / "key"
        self.token.write_text("a" * 64)
        self.token.chmod(0o600)
        self.port_patch = mock.patch.object(lc, "DEFAULT_PORT", self.server.server_port)
        self.port_patch.start()
        self.addCleanup(self.port_patch.stop)
        self.models = {"models": [{"name": "kev-latest", "run": lc.PINNED_RUN, "backend": "mlx", "truncate_states": False, "temperature": 2.41}]}
        self.response = copy.deepcopy(RESPONSE)
        self.delay, self.status, self.redirect, self.calls = 0, 200, False, 0

    def client(self, **kwargs):
        return lc.Client(self.token, **kwargs)

    def test_valid_roundtrip_and_proxy_is_ignored(self):
        with mock.patch.dict(os.environ, {"http_proxy": "http://198.51.100.1:1", "HTTP_PROXY": "http://198.51.100.1:1", "NO_PROXY": ""}):
            result = self.client().request("ordinary state", QUESTIONS)
        self.assertEqual(result, RESPONSE)
        self.assertEqual(self.authorization, "Bearer " + "a" * 64)
        self.assertEqual(self.sent["state"], "ordinary state")

    def test_reject_remote_alias_credentials_paths_and_other_ports(self):
        for url in ("http://localhost:8019", "https://127.0.0.1:8019", "http://127.0.0.1:9", "http://127.0.0.1:8019/", "http://127.0.0.1:8019@evil.test", "http://[::1]:8019"):
            with self.subTest(url=url), self.assertRaises(lc.ClientError):
                self.client(base_url=url)

    def test_private_regular_token_required(self):
        self.token.chmod(0o644)
        with self.assertRaises(lc.ClientError):
            self.client()
        self.token.chmod(0o600)
        other = self.token.with_name("link")
        other.symlink_to(self.token)
        with self.assertRaises(lc.ClientError):
            lc.Client(other)

    def test_identity_backend_and_truncation_checks(self):
        for field, value in (("run", "different"), ("backend", "torch"), ("truncate_states", True), ("temperature", float("nan"))):
            self.models["models"][0][field] = value
            with self.subTest(field=field), self.assertRaises(lc.ClientError):
                self.client().get_models()
            self.setUpModel()

    def setUpModel(self):
        self.models = {"models": [{"run": lc.PINNED_RUN, "backend": "mlx", "truncate_states": False, "temperature": 2.41}]}

    def test_redirects_are_not_followed(self):
        self.redirect = True
        with self.assertRaisesRegex(lc.ClientError, "HTTP 302"):
            self.client().get_models()

    def test_http_error_body_does_not_expose_token(self):
        self.status = 500
        self.models = ("sensitive " + "a" * 64).encode()
        with self.assertRaises(lc.ClientError) as caught:
            self.client().get_models()
        self.assertEqual(str(caught.exception), "HTTP 500")

    def test_timeout_is_sanitized(self):
        self.delay = .1
        with self.assertRaisesRegex(lc.ClientError, "timed out"):
            self.client(timeout=.01).get_models()

    def test_invalid_json_and_nonfinite_json(self):
        for value in (b"invalid", b'{"models": NaN}', b"[]"):
            self.models = value
            with self.subTest(value=value), self.assertRaises(lc.ClientError):
                self.client().get_models()

    def test_admission_does_not_contact_model(self):
        for state, questions in (("x" * (lc.MAX_STATE_BYTES + 1), QUESTIONS), (float("nan"), QUESTIONS), ("x", {"q": {"type": "execute", "criteria": {}}}), ("x", {"q": {"type": "noul", "label": True}})):
            with self.subTest(state_type=type(state).__name__), self.assertRaises(lc.ClientError):
                self.client().request(state, questions)
        self.assertEqual(self.calls, 0)

    def test_missing_extra_or_unknown_answer(self):
        for change in (lambda a: a.pop("level"), lambda a: a.update(extra={}), lambda a: a["level"].update(type="execute")):
            self.response = copy.deepcopy(RESPONSE)
            change(self.response["answers"])
            with self.assertRaises(lc.ClientError):
                self.client().request("x", QUESTIONS)

    def test_bad_distributions_and_scalar_ranges(self):
        cases = [
            ("route", "probabilities", {"a": .3, "b": .3}),
            ("route", "probabilities", {"a": .8, "c": .2}),
            ("route", "probabilities", {"a": float("inf"), "b": .2}),
            ("route", "choice", "b"),
            ("route", "confidence", True),
            ("relevant", "noul", -.1),
            ("level", "score", .1),
            ("level", "legend", {"0": "low"}),
        ]
        for question, field, value in cases:
            self.response = copy.deepcopy(RESPONSE)
            self.response["answers"][question][field] = value
            with self.subTest(question=question, field=field), self.assertRaises(lc.ClientError):
                self.client().request("x", QUESTIONS)

    def test_truncated_usage_and_unknown_top_level(self):
        for extra in ({"truncated": True}, {"unknown": 1}, {"usage": {"input_tokens": 1, "output_tokens": 1, "state_tokens": 9, "state_tokens_used": 8}}):
            self.response = {**copy.deepcopy(RESPONSE), **extra}
            with self.subTest(extra=extra), self.assertRaises(lc.ClientError):
                self.client().request("x", QUESTIONS)


class TestRuntime(unittest.TestCase):
    def test_process_identity_mismatch_never_signals_process(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            runtime.write_private(data / "server.json", {"pid": 12345, "identity": "old process"})
            with mock.patch.object(runtime, "identity", return_value="another process"), mock.patch.object(runtime.os, "kill") as kill:
                with self.assertRaises(lc.ClientError):
                    runtime.stop(None, data)
                kill.assert_not_called()

    def test_runtime_rejects_unregistered_model_before_spawning(self):
        args = type("Args", (), {"run": "unregistered/model"})()
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(runtime.subprocess, "Popen") as spawn:
            with self.assertRaises(lc.ClientError):
                runtime.start(args, Path(folder))
            spawn.assert_not_called()

    def test_private_receipt_writer_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "original"
            target.write_text("unchanged")
            link = Path(folder) / "receipt"
            link.symlink_to(target)
            with self.assertRaises(OSError):
                runtime.write_private(link, {"changed": True})
            self.assertEqual(target.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
