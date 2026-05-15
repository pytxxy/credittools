import importlib
import sys
import types
import unittest
from types import SimpleNamespace
from unittest import mock


def _install_creditutils_stub():
    if "creditutils.trivial_util" in sys.modules:
        return

    creditutils_pkg = types.ModuleType("creditutils")
    trivial_util_mod = types.ModuleType("creditutils.trivial_util")
    trivial_util_mod.measure_time = lambda func, *args, **kwargs: func(*args, **kwargs)
    creditutils_pkg.trivial_util = trivial_util_mod
    sys.modules["creditutils"] = creditutils_pkg
    sys.modules["creditutils.trivial_util"] = trivial_util_mod


def _install_requests_stub():
    if "requests" in sys.modules:
        return

    requests_mod = types.ModuleType("requests")

    def _unexpected_request(*args, **kwargs):
        raise AssertionError("network requests are not expected in this test")

    requests_mod.get = _unexpected_request
    requests_mod.put = _unexpected_request
    requests_mod.delete = _unexpected_request
    requests_mod.post = _unexpected_request
    sys.modules["requests"] = requests_mod


class InlineThread:
    def __init__(self, target, args=(), kwargs=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}

    def start(self):
        self.target(*self.args, **self.kwargs)

    def join(self):
        return None


class FakeBuilderClient:
    def __init__(self):
        self.calls = []

    def check_call_builder(self, data):
        self.calls.append(dict(data))
        return {"code": "0"}


class AndroidClientProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_creditutils_stub()
        _install_requests_stub()
        cls.android_client = importlib.import_module("android_client")

    def _build_args(self):
        return SimpleNamespace(
            to_update=True,
            is_debug=False,
            req_name="test",
            req_passwd="Test",
            req_url="http://example.com/api/flow",
            job_name="android_app",
            job_url="http://jenkins/job/android_app/",
            job_build_name="#1",
            job_build_url="http://jenkins/job/android_app/1/",
            app_codes="tchk,txxy",
            ver_envs="qa,prod",
            ver_names='{"tchk":"1.0.0","txxy":"2.0.0"}',
            ver_codes='{"tchk":1,"txxy":2}',
            ver_nos='{"tchk":1,"txxy":2}',
            api_vers='{"tchk":"v1","txxy":"v2"}',
            is_test=False,
            to_align=True,
            to_upload=True,
            splash_type=3,
            with_bundle_format=False,
            channel="chan_a,chan_b",
            demo_label="normal",
            branch="develop",
            minify_enabled=True,
            need_notify=False,
            to_upload_bugly=True,
            release_debuggable=False,
            with_api_encrypt=True,
        )

    def test_process_expands_each_env_app_and_channel(self):
        fake_client = FakeBuilderClient()
        args = self._build_args()

        with mock.patch.object(self.android_client.Client, "new_client", return_value=fake_client):
            with mock.patch.object(self.android_client.threading, "Thread", InlineThread):
                app_client = self.android_client.AppClient(args)
                is_success = app_client.process()

        self.assertTrue(is_success)
        self.assertEqual(8, len(fake_client.calls))
        self.assertEqual({"chan_a", "chan_b"}, {call["channel"] for call in fake_client.calls})

        expected_tasks = {
            ("qa", "tchk", "chan_a"),
            ("qa", "tchk", "chan_b"),
            ("qa", "txxy", "chan_a"),
            ("qa", "txxy", "chan_b"),
            ("prod", "tchk", "chan_a"),
            ("prod", "tchk", "chan_b"),
            ("prod", "txxy", "chan_a"),
            ("prod", "txxy", "chan_b"),
        }
        actual_tasks = {(call["env"], call["product"], call["channel"]) for call in fake_client.calls}
        self.assertEqual(expected_tasks, actual_tasks)


if __name__ == "__main__":
    unittest.main()
