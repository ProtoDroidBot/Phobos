"""Python 3 controller for the isolated Python 2 native-loader worker."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile


class NativeWorkerError(RuntimeError):
    pass


def find_python2(explicit=None):
    bundled_host = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "tools", "py27host.exe")
    )
    candidates = [
        explicit,
        os.environ.get("PHOBOS_PYTHON2"),
        bundled_host,
        shutil.which("python2.7"),
        shutil.which("python2"),
        r"C:\Python27\python.exe",
        r"C:\Python27-x64\python.exe",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return None


def find_legacy_code_root(build=None, explicit=None):
    candidates = [explicit, os.environ.get("PHOBOS_LEGACY_CODE_ROOT")]
    if build is not None:
        candidates.extend(
            [
                os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "client_code", str(build))),
            ]
        )
    for candidate in candidates:
        if candidate and (
            os.path.isfile(os.path.join(candidate, "__future__.pyc"))
            or os.path.isfile(os.path.join(candidate, "__future__.py"))
        ):
            return os.path.abspath(candidate)
    return None


def _restore_worker_value(value):
    if isinstance(value, list):
        return [_restore_worker_value(item) for item in value]
    if isinstance(value, dict):
        if value.get("$type") == "bytes" and value.get("encoding") == "base64":
            return base64.b64decode(value["data"])
        return {key: _restore_worker_value(item) for key, item in value.items()}
    return value


class NativeWorker:
    def __init__(self, python2_executable, client_bin64, legacy_code_root=None, timeout=600):
        self.python2_executable = python2_executable
        self.client_bin64 = os.path.abspath(client_bin64)
        self.legacy_code_root = legacy_code_root
        self.timeout = timeout
        self.worker_script = os.path.join(os.path.dirname(__file__), "py2_worker.py")

    @property
    def available(self):
        return bool(self.python2_executable and os.path.isfile(self.python2_executable))

    def _execute(self, request):
        if not self.available:
            raise NativeWorkerError(
                "a 64-bit Python 2.7 interpreter is required; set PHOBOS_PYTHON2 or pass --python2"
            )
        with tempfile.TemporaryDirectory(prefix="phobos-py2-") as temp_dir:
            request_path = os.path.join(temp_dir, "request.json")
            response_path = os.path.join(temp_dir, "response.json")
            with open(request_path, "w", encoding="utf-8") as stream:
                json.dump(request, stream, ensure_ascii=True)
            environment = os.environ.copy()
            environment["PATH"] = self.client_bin64 + os.pathsep + environment.get("PATH", "")
            environment["PHOBOS_PYTHON27_DLL"] = os.path.join(self.client_bin64, "python27.dll")
            if self.legacy_code_root:
                environment["PYTHONPATH"] = self.legacy_code_root
            completed = subprocess.run(
                [self.python2_executable, "-S", self.worker_script, request_path, response_path],
                cwd=self.client_bin64,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            if not os.path.isfile(response_path):
                raise NativeWorkerError(
                    "Python 2 worker exited {} without a response: {}".format(
                        completed.returncode, completed.stderr.strip() or completed.stdout.strip()
                    )
                )
            with open(response_path, "r", encoding="utf-8") as stream:
                response = json.load(stream)
            if not response.get("ok"):
                raise NativeWorkerError(response.get("error", "unknown Python 2 worker failure"))
            return _restore_worker_value(response.get("data"))

    def load_fsd(self, module_name, loader_path, data_path):
        return self._execute(
            {
                "schemaVersion": 1,
                "action": "load_fsd",
                "moduleName": module_name,
                "loaderPath": os.path.abspath(loader_path),
                "dataPath": os.path.abspath(data_path),
                "bin64": self.client_bin64,
            }
        )

    def validate_planet_template(self, dll_path, buffer_value, num_bands):
        return self._execute(
            {
                "schemaVersion": 1,
                "action": "planet_coefficients",
                "dllPath": os.path.abspath(dll_path),
                "bufferBase64": base64.b64encode(buffer_value).decode("ascii"),
                "numBands": int(num_bands),
                "bin64": self.client_bin64,
            }
        )
