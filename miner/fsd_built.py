#===============================================================================
# Copyright (C) 2014-2019 Anton Vorobyov
#
# This file is part of Phobos.
#
# Phobos is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Phobos is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Phobos. If not, see <http://www.gnu.org/licenses/>.
#===============================================================================


import contextlib
import gc
import hashlib
import importlib
import os
import re
import shutil
import struct
import sys
import tempfile

from util import EveNormalizer, cachedproperty
from .base import BaseMiner


class FsdBuiltMiner(BaseMiner):

    name = 'fsd_built'

    def __init__(self, resbrowser, translator, client_profile=None, native_worker=None):
        self._resbrowser = resbrowser
        self._translator = translator
        self._client_profile = client_profile
        self._native_worker = native_worker
        self.__temp_dir = None

    @property
    def backend_name(self):
        if self._client_profile is not None and self._client_profile.is_legacy_py27:
            return 'python2-native-worker'
        return 'python3-native-loader'

    def contname_iter(self):
        for container_name in sorted(self._contname_fsdfiles_map):
            yield container_name

    def get_data(self, container_name, language=None, verbose=False, **kwargs):
        try:
            loader_respath, data_respath = self._contname_fsdfiles_map[container_name]
        except KeyError:
            self._container_not_found(container_name)
        else:
            loader_filename = loader_respath.split('/')[-1]
            loader_info = self._resbrowser.get_file_info(loader_respath)
            data_info = self._resbrowser.get_file_info(data_respath)
            if self._client_profile is not None and self._client_profile.is_legacy_py27:
                if self._native_worker is None:
                    raise PlatformError('legacy client native loader requires a configured Python 2 worker')
                loader_modname = os.path.splitext(loader_filename)[0]
                direct_loader_path = os.path.join(
                    self._client_profile.eve_path,
                    self._client_profile.server_alias,
                    *loader_respath[len('app:/'):].split('/'),
                )
                if os.path.isfile(direct_loader_path):
                    with open(direct_loader_path, 'rb') as direct_loader:
                        direct_hash = hashlib.md5(direct_loader.read()).hexdigest()
                    if direct_hash != loader_info.file_hash:
                        raise ValueError('direct loader checksum does not match resource index')
                    loader_path = direct_loader_path
                else:
                    loader_path = loader_info.file_abspath
                normalized_data = self._native_worker.load_fsd(
                    loader_modname,
                    loader_path,
                    data_info.file_abspath,
                )
                self._translator.translate_container(normalized_data, language, verbose=verbose)
                return normalized_data
            if not self._platform_supported(os.name, sys.platform, struct.calcsize('P') * 8):
                msg = 'need 64-bit Python on Windows or macOS to execute loader'
                raise PlatformError(msg)

            with self._temp_dir() as temp_dir:
                sys.path.insert(0, temp_dir)

                loader_dest = os.path.join(temp_dir, loader_filename)
                if not os.path.isfile(loader_dest) or not self._compare_files(loader_info.file_abspath, loader_dest):
                    shutil.copyfile(loader_info.file_abspath, loader_dest)

                loader_modname = os.path.splitext(loader_filename)[0]
                loader_module = importlib.import_module(loader_modname)
                fsd_data = loader_module.load(data_info.file_abspath)
                normalized_data = EveNormalizer().run(fsd_data, loader_module=loader_module)

                sys.path.remove(temp_dir)
                del loader_module
                del sys.modules[loader_modname]
                gc.collect()

            self._translator.translate_container(normalized_data, language, verbose=verbose)
            return normalized_data

    def source_metadata(self, container_name):
        pair = self._contname_fsdfiles_map.get(container_name)
        if pair is None:
            return None
        return [
            self._file_info_metadata(self._resbrowser.get_file_info(resource_path))
            for resource_path in pair
        ]

    @cachedproperty
    def _contname_fsdfiles_map(self):
        """
        Map between container names and locations of FSD loader/data.
        Format: {container name: (fsd loader file path, fsd data file path)}
        """
        loaders = {}
        datas = {}
        for resource_path in self._resbrowser.respath_iter():
            m = re.match(
                r'^app:/(?:.+/)?bin64/(\w+/)*(?P<name>\w+)Loader\.(?:pyd|so)$',
                resource_path,
                flags=re.UNICODE,
            )
            if m:
                loaders[m.group('name').lower()] = resource_path
                continue
            m = re.match(r'^res:/staticdata/(\w+/)*(?P<name>\w+).fsdbinary$', resource_path, flags=re.UNICODE)
            if m:
                datas[m.group('name').lower()] = resource_path
                continue
        contname_fsdfiles_map = {}
        for container_name in set(loaders).intersection(datas):
            contname_fsdfiles_map[container_name] = (loaders[container_name], datas[container_name])
        return contname_fsdfiles_map

    @contextlib.contextmanager
    def _temp_dir(self):
        """A context manager for creating and then deleting a temporary directory."""
        if self.__temp_dir is None:
            self.__temp_dir = tempfile.mkdtemp(prefix='phobos-')
        try:
            yield self.__temp_dir
        # Try to remove folder, but be silent if it fails, as it is to be expected, because
        # python process which has used library from this folder is still running
        finally:
            error_data = []

            def on_error(*args, **kwargs):
                error_data.append((args, kwargs))

            shutil.rmtree(self.__temp_dir, ignore_errors=False, onerror=on_error)
            # Avoid creating new dirs in future if we haven't removed this one
            if not error_data:
                self.__temp_dir = None

    def _compare_files(self, file1_path, file2_path):
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            return f1.read() == f2.read()

    @staticmethod
    def _platform_supported(os_name, sys_platform, pointer_bits):
        if pointer_bits != 64:
            return False
        return os_name == 'nt' or sys_platform == 'darwin'


class PlatformError(Exception):
    """Raised when FSD built miner is used on incorrect platform."""
    pass
