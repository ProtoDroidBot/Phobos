
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
#from collections import OrderedDict
import json
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
                    


        def vectorstuff(raw_fsd):
            #print(raw_fsd)
            #print(raw_fsd.data)
            #print(raw_fsd.schema)
            #fsd_list.append("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))
            for item1 in raw_fsd.__dir__():
                #result = raw_fsd
                #print(result)
                if item1.startswith("__"):
                    continue
                else:
                    #print("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))
                    return("Vector: " + str(raw_fsd.data) + "Schema: " + str(raw_fsd.schema))
  

        def dictstuff(raw_fsd):
            test2 = []
            #print(original)
            #print(raw_fsd)
            try:
                for item in raw_fsd.__schema__['attributes']:
                    #print(item)
                    test2.append(str(raw_fsd[item]))
                    #print(pre_fsd_data[item].__dir__())
                    for item2 in raw_fsd[item].__dir__():
                        if item2.startswith("__"):
                            continue
                        else:
                            test = getattr(raw_fsd[item],item2)
                            #print(test)
                            #fsd_list.append(str(dictstuff(getattr(raw_fsd,item))))
                    test2.append(test)
            except:
                if type(raw_fsd) == objectLoader.ObjectLoader:
                    for item in raw_fsd.__schema__['attributes'].items():
                        test2.append(item)
                        
                        #test2.append(objstuff(raw_fsd.__getitem__(item)))
                else:
                    for item in raw_fsd:
                        test2.append(str(raw_fsd[item]))
                        #print(pre_fsd_data[item].__dir__())
                        for item2 in raw_fsd[item].__dir__():
                            if item2.startswith("__"):
                                continue
                            else:
                                test = getattr(raw_fsd[item],item2)
                                #print(test)
                                #fsd_list.append(str(dictstuff(getattr(raw_fsd,item))))
                        test2.append(test)
            return test2
                            

        def objstuff(raw_fsd):
            testing1 = raw_fsd.__schema__['attributes']
            main = []
            for item1 in testing1:
                nuked = raw_fsd.__getattr__(item1)
                if type(nuked) == dictLoader.DictLoader:
                    print(nuked)
                    test1 = dictstuff(nuked)
                    main.append(test1)
                elif type(nuked) == miscLoaders.VectorLoader:
                    test1 = vectorstuff(nuked)
                    main.append(test1)
                else:
                    testing2 = (nuked.__schema__['attributes'])
                    for item2 in testing2:
                        item3 = (nuked.__getattr__(item2))
                        if type(item3) == dictLoader.DictLoader:
                            main.append(dictstuff(item3))
                            #return item4
                        if type(item2) == miscLoaders.VectorLoader:
                            #item4 = vectorstuff(item3)
                            main.append(vectorstuff(item3))
                            #return item4  
                            #return result
                        else:
                            #print(raw_fsd.__getattr__(item))
                            main.append(item3)
                            #print(raw_fsd.Get[item])
                        #return main
                            #fsd_list.append(str(result))
                        #main = item
            #print(main)
            return(main)


        schema = None
        pre_fsd_data = binLoader.LoadFSDDataInPython(fsd_file_path, schema, False, None)

        fsd_list = []
        test = ""
        fsd_tuple = {}
        print(type(pre_fsd_data))
        if type(pre_fsd_data) == dictLoader.DictLoader:
            for item in pre_fsd_data:
                #fsd_list = pre_fsd_data[item]
                #print(pre_fsd_data[item])
                fsd_list.append(str(pre_fsd_data[item]))
                #print(pre_fsd_data[item].__dir__())
                if type(pre_fsd_data[item]) == objectLoader.ObjectLoader:
                    test = dictstuff(pre_fsd_data[item])
                    fsd_list.append(test)
            #print(fsd_list)
            return fsd_list
        elif type(pre_fsd_data) == listLoader:
            for item in pre_fsd_data:
                #fsd_list = pre_fsd_data[item]
                #print(pre_fsd_data[item])
                fsd_list.append(str(pre_fsd_data[item]))
                #print(pre_fsd_data[item].__dir__())
                if type(pre_fsd_data[item]) == objectLoader.ObjectLoader:
                    test = objstuff(pre_fsd_data[item])
                    fsd_list.append(test)
            #print(fsd_list)
            return fsd_list
        elif type(pre_fsd_data) == objectLoader.ObjectLoader:
            #print(pre_fsd_data)
            
            fsd_list.append(objstuff(pre_fsd_data))
            return fsd_list
        elif type(pre_fsd_data) == dictLoader.IndexLoader:
            #print(list(pre_fsd_data.items()))
            for item in list(pre_fsd_data.items()):
                #print(item)
                fsd_list.append(str(item))
            #fsd_list = json.dumps((test),indent=1)
            return fsd_list
        elif type(pre_fsd_data) == dictLoader.MultiIndexLoader:
            #pre_fsd_data2 = pre_fsd_data.items()
            fsd_tuple = list(pre_fsd_data.items())
            #print(fsd_list)
            for item in fsd_tuple:
                #fsd_list.append(str(objstuff(item)))
                #print(item[1])
                fsd_list.append(str(dictstuff(item[1])))
            return fsd_list
            #fsd_list = str(pre_fsd_data.items())
            #fsd_list.append(str(item[1]))
            #print(getattr(pre_fsd_data, item))
            #result = item
            #print(type(item))

                #except:
                #return None


        else: #This should never trigger, and IndexLoader/MultiIndexLoader will error out the main loop anyway, so the data gets pushed to an alternate path
            #test = json.dumps((pre_fsd_data),indent=1)
            return fsd_list
           


        
    def get_data(self, container_name, language=None, verbose=False, **kwargs):
        try:
            resource_path = self._contname_respath_map[container_name]
        except KeyError:
            self._container_not_found(container_name)
        else:
            file_path = self._resbrowser.get_file_info(resource_path).file_abspath
            fsd_list = self.fsd_parser(file_path)
            #print(str(fsd_list))
            return str(fsd_list)
            
                
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
