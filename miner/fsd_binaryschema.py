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
from collections import OrderedDict
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

    def fsd_parser(self, fsd_file_path):
        codeccp = self._resbrowser.get_file_info('app:/code.ccp').file_abspath
        sys.path.insert(0, codeccp)
        import fsd
        import fsd.schemas
        import fsd.schemas.binaryLoader as binLoader
        import fsd.schemas.loaders.dictLoader as dictLoader
        #import fsd.schemas.loaders.dictLoader as DictLoader
        import fsd.schemas.loaders.listLoader as listLoader
        import fsd.schemas.loaders.objectLoader as objectLoader
        import fsd.schemas.loaders as miscLoaders

        schema = None
        pre_fsd_data = binLoader.LoadFSDDataInPython(fsd_file_path, schema, False, None)

        fsd_list = []
        fsd_list2 = []
        fsd_tuple = {}

        try:
            #print(type(pre_fsd_data))
            if type(pre_fsd_data) == dictLoader.DictLoader:
                for item in pre_fsd_data:
                    fsd_list.append(str(pre_fsd_data[item]))
                #fsd_list.append((mini_fsd_parser(list(pre_fsd_data[item]))))
            elif type(pre_fsd_data) == listLoader:
                for item in pre_fsd_data:
                    fsd_tuple.append(str(pre_fsd_data[item]))
                #fsd_list.append(str(mini_fsd_parser(pre_fsd_data[item])))
            elif type(pre_fsd_data) == objectLoader:
                for item in pre_fsd_data:
                    fsd_tuple.append(str(pre_fsd_data[item]))
                #fsd_list.append(str(mini_fsd_parser(pre_fsd_data[item])))
            elif type(pre_fsd_data) == dictLoader.IndexLoader:
                fsd_tuple2 = list(pre_fsd_data.items())
                for item in fsd_tuple2:
                    fsd_list.append(str(item[1]))
            elif type(pre_fsd_data) == dictLoader.MultiIndexLoader:
                fsd_tuple2 = list(pre_fsd_data.items())
                for item in fsd_tuple2:
                    fsd_list.append(str(item[1]))
                    for subitem2 in item[1].__dir__():
                        try:
                            reinput = item[1].__getitem__(subitem2)  
                            if reinput == "None" or reinput == None or reinput == []:
                                continue
                            else:
                                #TODO: Add better documentation as to what the F### this section does
                                if type(reinput) == dictLoader.DictLoader:
                                    try:
                                        for item in reinput:
                                            fsd_list.append(str(reinput[item]))
                                    except:
                                        continue
                                elif type(reinput) == miscLoaders.VectorLoader:
                                    try:
                                        fsd_list.append("OUTEROBJ:"+str(item[1])+":"+str(item[1].__getitem__(subitem2))+":LAYER1:"+str(subitem2)+":INNEROBJ:"+str(reinput)+":VECTOR_SCHEMA:"+str(reinput.schema)+":DATA:"+str((reinput.data)))
                                    except:
                                        continue
                                elif type(reinput) == objectLoader:
                                    for item in reinput:
                                        fsd_list.append(str(reinput[item]))
                            #except:
                            #return None

                        except:
                        #print("skipping variable " + subitem2)
                            continue

            else: #This should never trigger, and IndexLoader/MultiIndexLoader will error out the main loop anyway, so the data gets pushed to an alternate path
                fsd_list.append(str(pre_fsd_data))
        except:
            print("????!")
        finally:
            try:
                return fsd_list
            except:
                return None



        
    def get_data(self, container_name, language=None, verbose=False, **kwargs):
        try:
            resource_path = self._contname_respath_map[container_name]
        except KeyError:
            self._container_not_found(container_name)
        else:
            file_path = self._resbrowser.get_file_info(resource_path).file_abspath
            fsd_list = self.fsd_parser(file_path)
            return fsd_list
            
                
    #def check_type(self, object):
        

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