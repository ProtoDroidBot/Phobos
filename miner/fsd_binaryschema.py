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


import re
import sqlite3
import zipimport
import sys
import importlib.util

from miner.base import BaseMiner
from util import EveNormalizer, cachedproperty


class FsdBinaryMiner(BaseMiner):
    """Class, which fetches data from FSDLite format static cache files."""

    name = 'fsd_binary_schema'

    def __init__(self, resbrowser, translator):
        self._resbrowser = resbrowser
        self._translator = translator

    def contname_iter(self):
        for container_name in sorted(self._contname_respath_map):
            yield container_name

    def get_data(self, container_name, language=None, verbose=False, **kwargs):
        codeccp = self._resbrowser.get_file_info('app:/code.ccp').file_abspath
        sys.path.insert(0, codeccp)
        import fsd
        import fsd.schemas
        import fsd.schemas.binaryLoader as binLoader
        import fsd.schemas.loaders.dictLoader as dictLoader
        #import fsd.schemas.loaders.dictLoader as DictLoader
        import fsd.schemas.loaders.listLoader as listLoader
        import fsd.schemas.loaders.objectLoader as objectLoader
        try:
            resource_path = self._contname_respath_map[container_name]
        except KeyError:
            self._container_not_found(container_name)
        else:
            file_path = self._resbrowser.get_file_info(resource_path).file_abspath
            #code_file = self._resbrowser.get_file_info('app:/code.ccp').file_abspath
            # code_file = re.match(r'app:/code.ccp$', resource_path, flags=re.UNICODE)
            #print (resource_path)
            try:
                schema_test = re.match(r'^res:/staticdata/(?P<fname>.+).schema$', resource_path)
                print(resource_path)
                #pre_fsd_data = binLoader.LoadFSDDataInPython(None, None, None, None)
                schema = self._resbrowser.get_file_info(schema_test).file_abspath
            except:
                schema = None
            finally:
                pre_fsd_data = binLoader.LoadFSDDataInPython(file_path, schema, False, None)
                fsd_list = []
                fsd_tuple = {}
                #fsd_data.update(keys)
                
                #if type(pre_fsd_data) == dictLoader.DictLoader:
                #keys = 
                #values = pre_fsd_data.values()
                #print(list(keys))
                #print(list(fsd_data))
                #normalized_data = EveNormalizer().run(fsd_data, loader_module=None)
                
                #for key in fsd_data:
                    #fsd_data[key] = pre_fsd_data.Get(key)
               
                print(type(pre_fsd_data))
                if type(pre_fsd_data) == dictLoader.DictLoader:
                    for item in pre_fsd_data:
                        #print(pre_fsd_data[item])
                        fsd_list.append(str(pre_fsd_data[item]))
                    return fsd_list
                elif type(pre_fsd_data) == dictLoader.IndexLoader:
                    fsd_tuple2 = list(pre_fsd_data.items())
                    #print
                    for item in fsd_tuple2:
                        #print(item[1])
                        fsd_list.append(str(item[1]))
                        #if type(item)
                    #self.cleanup_pass_values(fsd_data)
                    return fsd_list
                elif type(pre_fsd_data) == dictLoader.MultiIndexLoader:
                    fsd_tuple2 = list(pre_fsd_data.items())
                    #print
                    for item in fsd_tuple2:
                        #print(item[1])
                        fsd_list.append(str(item[1]))
                        #if type(item)
                    #self.cleanup_pass_values(fsd_data)
                    return fsd_list
                elif type(pre_fsd_data) == listLoader:
                    for item in pre_fsd_data:
                        #print(pre_fsd_data[item])
                        fsd_tuple.append(str(pre_fsd_data[item]))
                    return fsd_tuple
                elif type(pre_fsd_data) == objectLoader:
                    for item in pre_fsd_data:
                        #print(pre_fsd_data[item])
                        fsd_tuple.append(str(pre_fsd_data[item]))
                    return fsd_tuple
                else:
                    print("wtf")
                    return None
                    #schema = binLoader.LoadFSDDataInPython(file_path, self._resbrowser.get_file_info(schema_test).file_abspath)
            #print(fsd_data)
            
            #self._translator.translate_container(fsd_bin, language, verbose=verbose)
        
    @cachedproperty
    def _contname_respath_map(self):
        """
        Map between container names and resource path names to static cache files.
        Format: {container path: resource path to static cache}
        """
        contname_respath_map = {}
        for resource_path in self._resbrowser.respath_iter():
            # Filter by resource file path first
            container_name = self.__get_container_name(resource_path)
            if container_name is None:
                continue
            # Now, check if it's actually sqlite database and if it has cache table
            if self.__check_cache(resource_path):
                continue
            contname_respath_map[container_name] = resource_path
        return contname_respath_map

    def __get_container_name(self, resource_path):
        """
        Validate resource path and return stripped resource
        name if path is valid, return None otherwise.
        """
        m = re.match(r'^res:/staticdata/(?P<fname>.+).static$', resource_path)
        if not m:
            return None
        return m.group('fname')

    def __check_cache(self, resource_path):
        """Check if file is actually SQLite database and has cache table."""
        file_path = self._resbrowser.get_file_info(resource_path).file_abspath
        try:
            dbconn = sqlite3.connect(file_path)
            c = dbconn.cursor()
            c.execute('select count(*) from sqlite_master where type = \'table\' and name = \'cache\'')
        except KeyboardInterrupt:
            raise
        except:
            has_cache = False
        else:
            has_cache = False
            for row in c:
                has_cache = bool(row[0])
        return has_cache