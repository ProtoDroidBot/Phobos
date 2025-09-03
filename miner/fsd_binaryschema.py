
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
                    
        #fsd_list3 = []

        def vectorstuff(raw_fsd):
            #print(raw_fsd)
            #print(raw_fsd.data)
            #print(raw_fsd.schema)
            fsd_list.append("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))
            for item1 in raw_fsd.__dir__():
                #result = raw_fsd
                #print(result)
                if item1.startswith("__"):
                    continue
                else:
                    #print("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))
                    fsd_list.append("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))
  

        def dictstuff(raw_fsd,layer):
            #print(type(raw_fsd))
            for item1 in raw_fsd:
                #print(item1)
                #print(type(item1))

                if type(item1) == int:
                    #print(("#")*layer + str(raw_fsd) + "; " + str(item1) + "; " + str(raw_fsd))
                    fsd_list.append(("#")*layer + str(raw_fsd) + "; " + str(item1) + "; " + str(raw_fsd))
                    for item2s in raw_fsd[item1].__dir__():
                        if item2s.startswith("__"):
                            continue
                        else:
                            #print(item2s)
                            item3 = (raw_fsd[item1].__getitem__(item2s))
                            fsd_list.append(str(raw_fsd[item1]) + "; ATTRIBUTE; " + str(item2s) + "; VALUE; " + str(item3))
                            if type(item3) == dictLoader.DictLoader:
                                dictstuff(item3,layer+1)
                            if type(item3) == miscLoaders.VectorLoader:
                                #print(item3)
                                vectest = vectorstuff(item3)
                                fsd_list.append(str(vectest))
                    continue
                if item1.startswith("__"):
                    continue

                else:
                    #print(item1)
                    for item2 in raw_fsd:
                        result = raw_fsd.__getitem__(item1) 
                        #print(result)
                        #print(str(getattr(raw_fsd[item], item2)))
                        item3 = (raw_fsd[item1].__getitem__(item2))
                        #print(item3)
                        fsd_list.append(str(raw_fsd[item1]) + "; ATTRIBUTE; " + str(item2) + "; VALUE; " + str(item3))
                        if type(item3) == dictLoader.DictLoader:
                            dictstuff(item3,layer+1)
                        if type(item3) == miscLoaders.VectorLoader:
                            #print(item3)
                            vectorstuff(item3)
                        #return item3
                            

        def objstuff(raw_fsd):
            if type(raw_fsd) == dictLoader.DictLoader:
                dictstuff(raw_fsd,1)
            if type(raw_fsd) == miscLoaders.VectorLoader:
                vectorstuff(raw_fsd)
            try:
                for item in raw_fsd.__dir__():
                    if item.startswith("__"):
                        continue
                    else:
                        #print(raw_fsd)
                            #print(item1)
                        result = raw_fsd.__getitem__(item) 
                        #print(result)
                            #print(item2)
                        if type(result) == dictLoader.DictLoader:
                            #print(type(result))
                            dictstuff(result,1)
                        if type(result) == miscLoaders.VectorLoader:
                            vectorstuff(result)
                        else:
                            fsd_list.append(str(result))

            except:
                #fsd_list.append(str(raw_fsd))
                pass

        schema = None
        pre_fsd_data = binLoader.LoadFSDDataInPython(fsd_file_path, schema, False, None)

        fsd_list = []
        fsd_list2 = []
        fsd_tuple = {}

        #print(type(pre_fsd_data))
        if type(pre_fsd_data) == dictLoader.DictLoader:
            dictstuff(pre_fsd_data,1)
        elif type(pre_fsd_data) == listLoader:
            for item in pre_fsd_data:
                fsd_tuple.append(str(pre_fsd_data[item]))
            #fsd_list.append(str(mini_fsd_parser(pre_fsd_data[item])))
        elif type(pre_fsd_data) == objectLoader.ObjectLoader:
            objstuff(pre_fsd_data)
            #fsd_list.append(str(mini_fsd_parser(pre_fsd_data[item])))
        elif type(pre_fsd_data) == dictLoader.IndexLoader:
            fsd_tuple2 = list(pre_fsd_data.items())
            for item in fsd_tuple2:
                fsd_list.append(str(item[1]))
        elif type(pre_fsd_data) == dictLoader.MultiIndexLoader:
            pre_fsd_data2 = pre_fsd_data.items()
            for item in pre_fsd_data2:
                #fsd_list.append(str(item[1]))
                #print(item)
                #result = item
                #print(type(item))
                fsd_list.append(str(item))
                for subitem3 in item:
                    fsd_list.append(str(subitem3))
                    objstuff(subitem3)

                    #except:
                    #return None


        else: #This should never trigger, and IndexLoader/MultiIndexLoader will error out the main loop anyway, so the data gets pushed to an alternate path
            fsd_list.append(str(pre_fsd_data))
        return fsd_list
           


        
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
