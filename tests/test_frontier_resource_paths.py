import configparser
import importlib.util
import os
import sys
import tempfile
import types
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))


class cachedproperty(object):
    def __init__(self, method):
        self.__method = method

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = self.__method(instance)
        setattr(instance, self.__method.__name__, value)
        return value


def load_module(module_name, relpath, extra_modules=None):
    extra_modules = extra_modules or {}
    saved = {}
    for name, module in extra_modules.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module
    try:
        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(ROOT, relpath),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, module in extra_modules.items():
            if saved[name] is None:
                del sys.modules[name]
            else:
                sys.modules[name] = saved[name]


class FrontierPathFixTests(unittest.TestCase):
    def test_resource_browser_supports_nested_frontier_paths(self):
        util_module = types.ModuleType('util')
        util_module.cachedproperty = cachedproperty
        resource_browser = load_module(
            'test_resource_browser',
            'util/resource_browser.py',
            {'util': util_module},
        )

        with tempfile.TemporaryDirectory() as eve_dir:
            nested_index = os.path.join(
                eve_dir,
                'stillness',
                'EVE.app',
                'Contents',
                'Resources',
                'build',
            )
            os.makedirs(nested_index)
            expected = os.path.join(nested_index, 'resfileindex.txt')
            with open(expected, 'w'):
                pass

            browser = resource_browser.ResourceBrowser(eve_dir, 'stillness')
            browser._resource_index = {
                'app:/EVE.app/Contents/Resources/build/start.ini': None,
            }

            self.assertEqual(browser._resolve_resfileindex_path(), expected)
            self.assertEqual(
                browser.find_resource_path('start.ini', prefix='app:/'),
                'app:/EVE.app/Contents/Resources/build/start.ini',
            )

    def test_metadata_uses_suffix_lookup_for_start_ini(self):
        configparser_module = types.ModuleType('ConfigParser')
        configparser_module.ConfigParser = configparser.ConfigParser
        miner_base_module = types.ModuleType('miner.base')

        class BaseMiner(object):
            def _container_not_found(self, container_name):
                raise AssertionError(container_name)

        miner_base_module.BaseMiner = BaseMiner

        metadata_module = load_module(
            'miner.metadata_test',
            'miner/metadata.py',
            {
                'ConfigParser': configparser_module,
                'miner.base': miner_base_module,
            },
        )

        class Browser(object):
            def __init__(self):
                self.lookup_calls = []
                self.info_calls = []

            def find_resource_path(self, suffix, prefix=None):
                self.lookup_calls.append((suffix, prefix))
                return 'app:/EVE.app/Contents/Resources/build/start.ini'

            def get_file_info(self, resource_path):
                self.info_calls.append(resource_path)
                return types.SimpleNamespace(file_abspath=self.start_ini_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            start_ini_path = os.path.join(temp_dir, 'start.ini')
            with open(start_ini_path, 'w') as start_ini:
                start_ini.write('[main]\nbuild = 12345\n')

            browser = Browser()
            browser.start_ini_path = start_ini_path
            miner = metadata_module.MetadataMiner(browser)
            miner.get_data('metadata')

            self.assertEqual(browser.lookup_calls, [('start.ini', 'app:/')])
            self.assertEqual(
                browser.info_calls,
                ['app:/EVE.app/Contents/Resources/build/start.ini'],
            )

    def test_fsd_built_accepts_macos_loader_paths(self):
        util_module = types.ModuleType('util')
        util_module.cachedproperty = cachedproperty

        class EveNormalizer(object):
            def run(self, fsd_data, loader_module=None):
                return fsd_data

        util_module.EveNormalizer = EveNormalizer
        miner_base_module = types.ModuleType('miner.base')

        class BaseMiner(object):
            def _container_not_found(self, container_name):
                raise AssertionError(container_name)

        miner_base_module.BaseMiner = BaseMiner

        fsd_built_module = load_module(
            'miner.fsd_built_test',
            'miner/fsd_built.py',
            {
                'util': util_module,
                'miner.base': miner_base_module,
            },
        )

        class Browser(object):
            def respath_iter(self):
                return iter((
                    'app:/EVE.app/Contents/Resources/build/bin64/foo/ExampleLoader.so',
                    'res:/staticdata/foo/Example.fsdbinary',
                ))

        miner = fsd_built_module.FsdBuiltMiner(Browser(), translator=None)

        self.assertTrue(fsd_built_module.FsdBuiltMiner._platform_supported('posix', 'darwin', 64))
        self.assertEqual(
            miner._contname_fsdfiles_map['example'],
            (
                'app:/EVE.app/Contents/Resources/build/bin64/foo/ExampleLoader.so',
                'res:/staticdata/foo/Example.fsdbinary',
            ),
        )


if __name__ == '__main__':
    unittest.main()
