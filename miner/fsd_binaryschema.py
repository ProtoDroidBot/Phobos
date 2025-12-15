
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
from collections import ChainMap
from miner.base import BaseMiner
from util import EveNormalizer, cachedproperty
from decimal import Decimal

class FsdBinaryMiner(BaseMiner):
    """Class, which fetches data from FSD Binary and Schema formatted static cache files."""

    name = 'fsd_binary_schema'

    def __init__(self, resbrowser, translator):
        self._resbrowser = resbrowser
        self._translator = translator

    def contname_iter(self):
        for container_name in sorted(self._contname_respath_map):
            yield container_name

    def fsd_parser(self, fsd_file_path, schema_path, container):
        #Bunch of preliminary things here and functions to aid us in processing the metric ton of FSD nested nonsense
        
        codeccp = self._resbrowser.get_file_info('app:/code.ccp').file_abspath
        sys.path.insert(0, codeccp)
        import fsd
        import fsd.schemas
        import fsd.schemas.binaryLoader as binLoader
        import fsd.schemas.loaders.dictLoader as dictLoader
        import fsd.schemas.loaders.listLoader as listLoader
        import fsd.schemas.loaders.objectLoader as objectLoader
        import fsd.schemas.loaders as miscLoaders
        
        # Function for repeated calls to format objectLoader variables. Please ensure you are calling this function with an object type = miscLoaders.VectorLoader
        # VectorLoader have both .schema and .data calls, which return the schema and data of the FSD Vector object respectively
        # Absolutely no guardrails on this function so if something breaks, good luck.
        def vectorstuff(raw_fsd, returnval):
            test1 = []
            test1.append({"vector_schema": (raw_fsd.schema)})
            #test1.append({"vector_data": (raw_fsd.data)})
            for coordinate in raw_fsd.data:
                test1.append(str(Decimal(coordinate)))
            return test1
  
        # Function for repeated calls to format objectLoader variables. Please ensure you are calling this function with an object type = dictLoader.DictLoader
        def dictstuff(raw_fsd, idx, returnval):
            ret2 = "??"
            fsd_complete_merge = {}
            fsd_temp_merge = []
            
            for items1 in raw_fsd:
                #fsd_complete_merge.append(str(idx))
                #print(idx)
                try:
                    #test3.append("FSD_DICT_debug: " + str(raw_fsd))
                    #test3.append({str(items1): str(raw_fsd[items1])})
                    if type(raw_fsd[items1]) == miscLoaders.VectorLoader:
                                #print("?")
                        fsd_temp_merge.append({(str(items1)): (vectorstuff(raw_fsd[items1], ret2))})
                    elif type(raw_fsd[items1]) == dictLoader.DictLoader:
                        #print("????1")
                        fsd_temp_merge.append({(str(items1)): (dictstuff(raw_fsd[items1], (items1), ret2))})
                    elif type(raw_fsd[items1]) == objectLoader.ObjectLoader:
                        #print("????2")
                        fsd_temp_merge.append({(str(items1)): (objstuff(raw_fsd[items1], (items1),  ret2))})
                    else:
                        try:
                            fsd_temp_merge.append({(str(items1)): str(Decimal(raw_fsd[items1]))})
                        except:
                            fsd_temp_merge.append({(str(items1)): str(raw_fsd[items1])})
                    
                except:
                    raise
            fsd_complete_merge = {k: v for d in fsd_temp_merge for k, v in d.items()}
            return fsd_complete_merge
        
        # Function for repeated calls to format objectLoader variables. Please ensure you are calling this function with an object type = objectLoader.ObjectLoader
        def objstuff(raw_fsd, idx, returnval):
            ret2 = "??"
            fsd_complete_merge = {}
            fsd_temp_merge = []
            #fsd_complete_merge.append(str(idx))

            if type(raw_fsd) == objectLoader.ObjectLoader:
                for items1 in raw_fsd.__dir__():
                    #main.append(str(idx))
                    #print(idx)
                    try:
                        if items1.startswith("__"):
                            continue
                        item2 = raw_fsd.__getattr__(items1)
                        #main.append(str(idx))
                        #main.append("FSD_OBJ_debug: " + str(raw_fsd))
                        #main.append({str(items1): str(item2)})
                        if type(item2) == miscLoaders.VectorLoader:
                            fsd_temp_merge.append({(str(items1)): (vectorstuff(item2, ret2))})
                        elif type(item2) == dictLoader.DictLoader:
                            #print("????1")
                            fsd_temp_merge.append({(str(items1)): (dictstuff(item2, (items1), ret2))})
                        elif type(item2) == objectLoader.ObjectLoader:
                            #print("????2")
                            fsd_temp_merge.append({(str(items1)): (objstuff(item2, (items1),  ret2))})
                        else:
                            try:
                                fsd_temp_merge.append({(str(items1)): str(Decimal(item2))})
                            except:
                                fsd_temp_merge.append({(str(items1)): str(item2)})
                        
                    except:
                        raise
                fsd_complete_merge = {k: v for d in fsd_temp_merge for k, v in d.items()}
            return fsd_complete_merge
        
        #### THIS IS WHERE THE CODE ACTUALLY STARTS WORKING ####
        pre_fsd_data = binLoader.LoadFSDDataInPython(fsd_file_path, schema_path, False, None)

        #test = []
        # If you see variables with test="??" here, it is a throwaway variable used to ensure we always get a return value. For some reason just having the three loader types with just the Binary FSD and index values didn't "actually return anything". IDK.

        # Used for if the type of the parsed container is an FSD Dictionary Type, part of the dictLoader library, 
        if type(pre_fsd_data) == dictLoader.DictLoader:

            # It needs to be like this list=[{}], sorry. Otherwise I get this fun little error: "unable to write data with JsonWriter - TypeError: Object of type set is not JSON serializable"
            # Or does it!?
            test="??"
            fsd_json_inter = (dictstuff(pre_fsd_data, str("FSD_DICT"), test))
            return (fsd_json_inter)
        
        # Used for if the type of the parsed container is an FSD Object, generic catchall for all entries labled with <FSD Object: (File path)>. Part of the objectLoader Library
        elif type(pre_fsd_data) == objectLoader.ObjectLoader:
            test="??"
            fsd_json_inter = (objstuff(pre_fsd_data, str("FSD_OBJ"), test))
            return (fsd_json_inter)

        
        # Used for if the type of the parsed container is an FSD Index, part of the dictLoader Library
        elif type(pre_fsd_data) == dictLoader.IndexLoader:
            test = "??"
            fsd_json_inter=[]
            for item in (pre_fsd_data.items()):
                #fsd_json.append(str("FSD_ENTRY: ") + str(item[0]))

                #print(item)
                for items in item:
                    #print(items)
                    if type(items) == objectLoader.ObjectLoader:
                        #print(item[items])
                        fsd_json_inter.append({str(item[0]): objstuff(items, item[0], test)})
                        #print(items)
                    elif type(items) == dictLoader.DictLoader:
                        #print(type(items))
                        fsd_json_inter.append({str(item[0]): dictstuff(items, item[0], test)})
                    elif type(items) == miscLoaders.VectorLoader:
                        #print(type(items))
                        fsd_json_inter.append({str(item[0]): vectorstuff(items, test)}) 
                    else:
                        #print(type(items))
                        fsd_json_inter.append({str(item[0]): str(items)})
            
            return dict({"Type: FSD Index": fsd_json_inter})
        
        # Used for if the type of the parsed container is an FSD Multi Index, part of the dictLoader Library. This one was an actual royal pain as it typically combines the dict, object, and vectorLoader Libraries in weird ways I haven't explored yet.
        elif type(pre_fsd_data) == dictLoader.MultiIndexLoader:
            test = "??"
            fsd_json_inter=[]
            for item in (pre_fsd_data.items()):
                #fsd_json.append(str("FSD_ENTRY: ") + str(item[0]))

                print(item[0])
                for items in item:
                    #print(items)
                    if type(items) == objectLoader.ObjectLoader:
                        #print(item[items])
                        fsd_json_inter.append({str(item[0]): objstuff(items, item[0], test)})
                        #print(items)
                    elif type(items) == dictLoader.DictLoader:
                        #print(type(items))
                        fsd_json_inter.append({str(item[0]): dictstuff(items, item[0], test)})
                    elif type(items) == miscLoaders.VectorLoader:
                        #print(type(items))
                        fsd_json_inter.append({str(item[0]): vectorstuff(items, test)}) 
                    else:
                        #print(type(items))
                        fsd_json_inter.append({str(item[0]): str(items)})
            return ({"Type: FSD Multi Index": fsd_json_inter})
            
        else: # This should never trigger except on ListLoader, and IndexLoader/MultiIndexLoader will error out the main loop anyway, so the data gets pushed to an alternate path
            # WIP WIP WIP, I need to read the spec for this ListLoader crap
            # Also there are two load strategies for ListLoader entries.
            fsd_json_inter = []
            try:
                
                for listItems in pre_fsd_data.items():
                    # This works fine?
                    fsd_json_inter.extend((listItems))
                    items2 = "Entry"
                    test = None
                    if type(listItems) == dictLoader.DictLoader:
                        #print(testing.schema['type'])
                        fsd_json_inter.append({str(listItems): (dictstuff(listItems, items2, test))})
                                      
                    elif type(listItems) == miscLoaders.VectorLoader:
                        #print(">")
                        fsd_json_inter.append({str(listItems): (vectorstuff(listItems,test))})
                    elif type(listItems) == objectLoader.ObjectLoader:
                        #print(">")
                        fsd_json_inter.append({str(listItems): (objstuff(listItems, items2, test))})
                    else:
                        fsd_json_inter.append((str(listItems)))
                        continue

            except:
                for listItems in pre_fsd_data:
                    # This does not work. :<
                    #fsd_json_inter.extend(str(listItems))
                    items2 = "Entry"
                    test = None
                    if type(listItems) == dictLoader.DictLoader:
                        #print(testing.schema['type'])
                        fsd_json_inter.append({str(listItems): (dictstuff(listItems, items2, test))})
                                      
                    elif type(listItems) == miscLoaders.VectorLoader:
                        #print(">")
                        fsd_json_inter.append({str(listItems): (vectorstuff(listItems,test))})
                    elif type(listItems) == objectLoader.ObjectLoader:
                        #print(">")
                        fsd_json_inter.append({str(listItems): (objstuff(listItems, items2, test))})
                    else:
                        fsd_json_inter.append((str(listItems)))
                        continue
            return ({"Type: FSD List": fsd_json_inter})
           


        
    def get_data(self, container_name, language=None, verbose=True, **kwargs):
        
        # If the data has a corresponding schema file, load it into the fsd_parser function, otherwise, treat it as None
        try:
            resource_path = self._contname_respath_map[container_name]
            schema_path=None
            try:
                schema_name = self._schemaname_respath_map[container_name]
                schema_path = self._resbrowser.get_file_info(schema_name).file_abspath
                #print(str(container_name) + " has a separate schema file, adding to parser")
            except KeyError:
                #schema_path = None
                #print(str(container_name) + " does not have a separate schema file, ignoring")
                pass
            finally:
                #print(schema_path)
                file_path = self._resbrowser.get_file_info(resource_path).file_abspath
                #print(container_name)
                fsd_list = self.fsd_parser(file_path, schema_path, container_name)
                return (fsd_list)
        except KeyError:
            self._container_not_found(container_name)
        #schema_path = None

            
                
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
        
    @cachedproperty    
    def _schemaname_respath_map(self):
        """
        Map between container names and resource path names to schema cache files.
        Format: {container path: resource path to schema cache}
        """
        contname_respath_map = {}
        for resource_path in self._resbrowser.respath_iter():
            # Filter by resource file path first
            container_name = self.__get_schema_container_name(resource_path)
            #print(container_name)
            if container_name is None:
                continue
            # Now, check if it's actually sqlite database and if it has cache table
            # This will ignore that file from being parsed!
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
        
    def __get_schema_container_name(self, schema_path):
        """
        Validate resource path and return stripped resource
        name if path is valid, return None otherwise.
        """
        s = re.match(r'^res:/staticdata/(?P<fname>.+).schema$', schema_path)
        #print(s)
        if not s:
            return None
        return s.group('fname')

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
