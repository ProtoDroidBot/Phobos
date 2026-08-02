import json
import os
import pickle
import tempfile
import unittest

from compat.client_profile import detect_client_profile
from compat.code_ccp import CodeCcpReader, PYTHON_27_MAGIC
from compat.legacy_fsd import load_and_materialize
from compat.legacy_runtime import prepare_legacy_runtime
from compat.manifest import ExtractionManifest
from compat.native_worker import NativeWorker, find_python2
from compat.pickle_compat import restricted_loads
from compat.serialization import bytes_envelope
from miner.unpickle import PickleMiner
from util.resource_browser import ResourceBrowser
from writer.json_writer import JsonWriter


EVE_ROOT = os.environ.get("PHOBOS_TEST_EVE", r"G:\evejs3396210-2\client\EVE")


class UnitCompatibilityTests(unittest.TestCase):
    def test_restricted_unpickler_rejects_globals(self):
        payload = pickle.dumps(os.system, protocol=2)
        with self.assertRaises(pickle.UnpicklingError):
            restricted_loads(payload, encoding="latin-1")

    def test_bytes_envelope_is_lossless(self):
        result = bytes_envelope(b"\x00\xffEVE")
        self.assertEqual(result["$type"], "bytes")
        self.assertEqual(result["length"], 5)
        self.assertEqual(result["data"], "AP9FVkU=")

    def test_json_writer_supports_binary_values(self):
        with tempfile.TemporaryDirectory() as folder:
            JsonWriter(folder).write("test", "bytes", {b"key": b"\x00\xff", 2: "two", "10": "ten"})
            with open(os.path.join(folder, "test", "bytes.json"), encoding="utf-8") as stream:
                result = json.load(stream)
        self.assertEqual(result["key"]["$type"], "bytes")
        self.assertEqual(result["key"]["length"], 2)
        self.assertEqual(result["2"], "two")
        self.assertEqual(result["10"], "ten")

    def test_manifest_records_failures(self):
        manifest = ExtractionManifest()
        manifest.record("miner", "container", "failed", backend="test", error="expected")
        with tempfile.TemporaryDirectory() as folder:
            path = manifest.write(folder)
            with open(path, encoding="utf-8") as stream:
                result = json.load(stream)
        self.assertEqual(result["summary"], {"failed": 1})
        self.assertEqual(len(manifest.failures), 1)

    def test_profile_defaults_to_python3_without_legacy_artifacts(self):
        with tempfile.TemporaryDirectory() as root:
            server = os.path.join(root, "tq")
            os.makedirs(server)
            with open(os.path.join(server, "start.ini"), "w", encoding="utf-8") as stream:
                stream.write("[main]\nbuild = 1\nversion = test\n")
            profile = detect_client_profile(root, "tq")
        self.assertEqual(profile.runtime, "python3")
        self.assertEqual(profile.build, 1)


@unittest.skipUnless(os.path.isfile(os.path.join(EVE_ROOT, "tq", "start.ini")), "build 3396210 is unavailable")
class Build3396210GoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = detect_client_profile(EVE_ROOT, "tq")
        cls.browser = ResourceBrowser(EVE_ROOT, "tq")

    def _static_paths(self, name):
        data_path = self.browser.get_file_path("res:/staticdata/{}.static".format(name))
        try:
            schema_path = self.browser.get_file_path("res:/staticdata/{}.schema".format(name))
        except KeyError:
            schema_path = None
        return data_path, schema_path

    def test_profile_detects_python27_build(self):
        self.assertEqual(self.profile.build, 3396210)
        self.assertEqual(self.profile.version, "24.01")
        self.assertEqual(self.profile.runtime, "legacy_py27")
        self.assertEqual(self.profile.code_magic, PYTHON_27_MAGIC.hex())

    def test_code_ccp_zlib_pipeline(self):
        reader = CodeCcpReader(self.profile.code_ccp_path)
        info = reader.inspect("fsd/schemas/binaryLoader.pyj")
        self.assertTrue(info.is_python27)
        self.assertEqual(info.pyc_size, 9228)
        self.assertEqual(
            info.sha256,
            "5f58a41c828aa78c00e29a5184fb52250af7c92e8116ad5a8f0625557ba1853b",
        )

    def test_planet_resources_templates(self):
        value = PickleMiner(self.browser).get_data("app:/res/planetResources")
        templates = value["depletionTemplates"]
        self.assertEqual(value["depletionStdDevMin"], 0.02)
        self.assertEqual(value["depletionStdDevMax"], 0.3)
        self.assertEqual(value["depletionStdDevStepSize"], 0.005)
        self.assertEqual(len(templates), 56)
        self.assertEqual(templates[0]["numBands"], 30)
        self.assertEqual(templates[0]["coefficientCount"], 900)
        self.assertEqual(templates[0]["bufferLength"], 3600)
        self.assertEqual(
            templates[0]["bufferSha256"],
            "fdb180abe1e5d4e4359dd5b424d8686eab18f7b34bfdb3dcf47ff57067dbab0e",
        )

    def test_embedded_schema_static(self):
        data_path, schema_path = self._static_paths("achievements")
        value = load_and_materialize(data_path, schema_path)
        self.assertEqual(len(value), 68)
        self.assertEqual(value[2]["achievementID"], 2)

    def test_external_indexed_schema_static(self):
        data_path, schema_path = self._static_paths("regions")
        value = load_and_materialize(data_path, schema_path)
        self.assertEqual(len(value), 114)
        self.assertEqual(value[10000001]["regionID"], 10000001)

    def test_python2_native_loader_worker(self):
        python2 = find_python2()
        if not python2:
            self.skipTest("Python 2 worker host is unavailable")
        runtime = prepare_legacy_runtime(self.profile.code_ccp_path, self.profile.build)
        worker = NativeWorker(
            python2,
            os.path.join(EVE_ROOT, "tq", "bin64"),
            legacy_code_root=runtime,
            timeout=120,
        )
        loader_path = os.path.join(EVE_ROOT, "tq", "bin64", "accountingEntryTypesLoader.pyd")
        data_path = self.browser.get_file_path("res:/staticdata/accountingentrytypes.fsdbinary")
        value = worker.load_fsd("accountingEntryTypesLoader", loader_path, data_path)
        self.assertEqual(len(value), 218)
        self.assertEqual(value["133"]["name"], "Duel Wager Payment")


if __name__ == "__main__":
    unittest.main()
