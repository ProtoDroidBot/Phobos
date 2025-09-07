
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

        def vectorstuff(raw_fsd, returnval):
            #print(raw_fsd)
            #print(raw_fsd.data)
            #print(raw_fsd.schema)
            test1 = []
            #fsd_list.append("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))

            #print("VECTOR; Above linked Entry; " + str(raw_fsd.data) + "; " + str(raw_fsd.schema))
            #return("Vector: " + str(raw_fsd.data) + "Schema: " + str(raw_fsd.schema))
            test1.append({"vector_schema": (raw_fsd.schema)})
            test1.append({"vector_data": (raw_fsd.data)})

            returnval = test1
            return returnval
  

        def dictstuff(raw_fsd, returnval):
            test3 = []
            ret2 = "??"
            #print(original)
            #print(raw_fsd)
            try:
                #print("a")
                for item in raw_fsd.__schema__['attributes']:
                    #print(item)
                    #test2.update(json.loads(json.dumps(dict(raw_fsd[item]))))
                    #print(test2)
                    if item.startswith("__"):
                        continue
                    else:
                        #print((raw_fsd[item]))

                        if type(raw_fsd[item]) == miscLoaders.VectorLoader:
                            test3.append({str(item):  vectorstuff(raw_fsd[item], ret2)}) 
                        elif type(raw_fsd[item]) == dictLoader.DictLoader:
                            test3.append({str(item): (dictstuff(raw_fsd[item], ret2))})
                            
                        elif type(raw_fsd[item]) == objectLoader.ObjectLoader:
                            test3.append({str(item): (raw_fsd[item], ret2)}) 
                            #test3.append({str(item): (raw_fsd[item])})
                        else:
                            test3.append({str(item): raw_fsd[item]})
                returnval = test3
                return returnval
            except:
                #print(type(raw_fsd))
                if type(raw_fsd) == objectLoader.ObjectLoader:
                    #print(type(raw_fsd))
                    for item in raw_fsd.__schema__['attributes']:
                        for item2 in raw_fsd.__schema__['attributes'][item]:
                            if item2.startswith("__"):
                                continue
                            else:
                                #print(raw_fsd[item][item2])
                                test3.append({str(item): str(item2), str(item2): (item2)})

                elif type(raw_fsd) == dictLoader.DictLoader:
                    #print("b")
                    #print(raw_fsd.__dir__())
                    try:
                        for item in raw_fsd.__schema__['attributes']:
                            for item2 in raw_fsd.__schema__['attributes'][item]:
                                if item2.startswith("__"):
                                    continue
                                else:
                                    #print(item2)
                                    test3.append({str(item): str(item2), str(item2): (raw_fsd[item][item2])})
                        returnval = test3
                        return returnval
                    except:
                        #print("c")
                        #test3.append(raw_fsd)
                        #print(raw_fsd)
                        for item in raw_fsd.items():
                            #test3.append({str((raw_fsd)): str(item)})
                            #print(">>")
                            #print(item)
                            for item2 in item:
                                #print(type(item2))
                                if type(item2) == dictLoader.DictLoader:
                                    test3.append({str(item): str(item2), str(item2): (dictstuff(item2, ret2))})
                                elif type(item2) == objectLoader.ObjectLoader:
                                    test3.append({str(item): str(item2), str(item2): (objstuff(item2, ret2))})
                                else:
                                    #print("?")
                                    test3.append({str(item): str(item2), str(item2): (item2)})
                        #print(test3)
                    returnval = test3
                    return returnval
                else:
                    try:
                        for item in raw_fsd:
                            #print(item)
                            try:
                                for item2 in raw_fsd[item].__dir__():
                                    if item2.startswith("__"):
                                        continue
                                    elif type(raw_fsd[item][item2]) == miscLoaders.VectorLoader:
                                        #print("?")
                                        test3.append({str(item): str(item2), str(item2): (vectorstuff(raw_fsd[item][item2], ret2))})
                                    elif type(raw_fsd[item][item2]) == dictLoader.DictLoader:
                                        #print("????1")
                                        test3.append({str(item): str(item2), str(item2): (dictstuff(raw_fsd[item][item2],ret2))})
                                    elif type(raw_fsd[item][item2]) == objectLoader.ObjectLoader:
                                        #print("????2")
                                        test3.append({str(item): str(item2), str(item2): (objstuff(raw_fsd[item][item2], ret2))})
                                    else:
                                        #print("????3")
                                        test3.append({str(item): str(item2), str(item2): (raw_fsd[item][item2])})
                                returnval = test3
                                return returnval
                            except:
                                #print(item)
                                for item2 in raw_fsd[item].__dir__():
                                    if item2.startswith("__"):
                                        continue
                                    #print(type(item2))
                                    #print(item2.values)
                                    #print(item2)
                                    #test3.append({str(item): (raw_fsd[item])})
                                    if type(item2) == miscLoaders.VectorLoader:
                                        #print("?1")
                                        test3.append({str(item): self.vectorstuff(item2)})
                                    elif type(item2) == dictLoader.DictLoader:
                                        #print("????2")
                                        test3.append({str(item): (dictstuff(item2, ret2))})
                                    elif type(item2) == objectLoader.ObjectLoader:
                                        #print("?1")
                                        test3.append({str(item): (objstuff(item2, ret2))})
                                    else:
                                        test3.append({str(item), str(item2)})
                                #test2 = test2 + test3
                                #print(test3)
                                returnval = test3
                                return returnval
                    except:
                        #print("?3")
                        returnval = test3
            return returnval
        
        def objstuff(raw_fsd, returnval):
            #testing1 = raw_fsd
            ret2 = "??"
            main = []
            if type(raw_fsd) == str or type(raw_fsd) == int or type(raw_fsd) == bool:
                #print(raw_fsd)
                return raw_fsd
            elif raw_fsd == None:
                raw_fsd = "None"
                return raw_fsd
            elif type(raw_fsd) == objectLoader.ObjectLoader:
                #print(type(raw_fsd))
                main2 = []
                for item2 in raw_fsd.__dir__():
                    #print(item2)
                    try:
                       
                        if item2.startswith("__"):
                            continue
                        #print(type(raw_fsd[item2]))
                        if type(raw_fsd[item2]) == dictLoader.DictLoader:
                            main2.append(({str(item2): dictstuff(raw_fsd[item2], ret2)}))
                            #return(main)
                        elif type(raw_fsd[item2]) == miscLoaders.VectorLoader:
                            #print("?5")
                            main2.append(({str(item2): vectorstuff(raw_fsd[item2], ret2)}))
                        elif type(raw_fsd[item2]) == objectLoader.ObjectLoader:
                            #print((raw_fsd[item2]))
                            main2.append(({str(item2): objstuff(raw_fsd[item2], ret2)}))
                        else:
                            #print(raw_fsd[item2])
                            main2.append(({str(item2): str(raw_fsd[item2])}))
                            #main2.append({"innertype": str(item2), "innerobj": raw_fsd[item2]})
                            #print (main)

                        #main2.append({str(item2), str(raw_fsd[item2])})
                    except:
                        pass
                #print(main2)
                returnval = main2
                return returnval
                #print(main2)
            else:
                #print(type(raw_fsd))
                try:
                    #print(testing1.schema)
                    for item1 in raw_fsd.schema:
                        #print("?")
                        if type(item1) == str or type(item1) == int or type(item1) == bool:
                            #print(item1)
                            return item1
                        #print(item1)
                        testing2 = (item1.schema['attributes'])
                        for item2 in testing2:
                            item3 = (getattr(item1, item2))
                            #print(" ! " + item3)
                            #main = ()
                            if type(item3) == dictLoader.DictLoader:
                                #print("??")
                                main.append((dictstuff(item3, ret2)))
                                #return item4
                            if type(item2) == miscLoaders.VectorLoader:
                                #item4 = vectorstuff(item3)
                                #print("?4")
                                main.append((vectorstuff(item3, ret2)))
                                #return item4  
                                #return result
                            else:
                                #print(raw_fsd.__getattr__(item))
                                #print("???")
                                main.append({str(item2), (item3)})
                                #print(raw_fsd.Get[item])
                            #return main
                                #fsd_list.append(str(result))
                    #print(main)
                    returnval = main
                    return returnval
                except:
                    #print(raw_fsd.__dir__())
                    try:
                        print("???")
                        for item2 in raw_fsd.__dir__():
                            try:
                                main2 = []
                                if item2.startswith("__"):
                                    continue
                                else:
                                    #print(type(raw_fsd[item2]))
                                    if type(raw_fsd[item2]) == dictLoader.DictLoader:
                                        main2.append(dictstuff(raw_fsd[item2], ret2))
                                        #return(main)
                                    elif type(raw_fsd[item2]) == miscLoaders.VectorLoader:
                                        #print("?5")
                                        main2.append(vectorstuff(raw_fsd[item2], ret2))
                                    if type(raw_fsd[item2]) == objectLoader.ObjectLoader:
                                        print((raw_fsd[item2]))
                                        main2.append((objstuff(raw_fsd[item2], ret2)))
                                    else:
                                        #print(raw_fsd[item2])
                                        main2.append({str(item2): (raw_fsd[item2])})
                                        #main2.append({"innertype": str(item2), "innerobj": raw_fsd[item2]})
                                        #print (main)
                            except:
                                pass
                        #print(main2)
                        returnval = main2
                        return returnval
                    except:
                        #print(str(raw_fsd.__dir__()))
                        pass
                    returnval = main2
                    return returnval
            #return({"objLoadertype": type(main), "objLoaderObj": str(main)})

        def deep_merge(dict1, dict2):
            merged = dict1.copy()
            for key, value in dict2.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged
        
        schema = None
        pre_fsd_data = binLoader.LoadFSDDataInPython(fsd_file_path, schema, False, None)

        fsd_list = []
        test = []
        print(type(pre_fsd_data))
        if type(pre_fsd_data) == dictLoader.DictLoader:
            fsd_json={str(fsd_file_path): []}
            try:
                for item in pre_fsd_data:
                    if type(item) == int:
                        fsd_json[str(fsd_file_path)].append({str(item): str(pre_fsd_data[item])})
                        try:
                            for items2 in pre_fsd_data[item].__schema__['attributes']:
                                #print(items2)
                                if type(pre_fsd_data[item][items2]) == dictLoader.DictLoader:
                                    test = "??"
                                    fsd_json[str(fsd_file_path)].append({str(items2): str(dictstuff(pre_fsd_data[item][items2], test))})
                                else:
                                    fsd_json[str(fsd_file_path)].append({str(items2): str(pre_fsd_data[item][items2])})
                        except:
                            continue
                    #elif type(item) == dictLoader.DictLoader:
                        #print("???")
            except:
                #print("?")
                for item in pre_fsd_data.keys():
                    if type(pre_fsd_data[item]) == dictLoader.DictLoader:
                        fsd_json[str(fsd_file_path)].append({str(item): json.dumps(dictstuff(pre_fsd_data[item], test))})
                    else:
                        fsd_json[str(fsd_file_path)].append({str(item): json.dumps((pre_fsd_data[item]))})
            

            return fsd_json
        
        #WIP WIP WIP
        elif type(pre_fsd_data) == listLoader:
            test = "??"
            for item in pre_fsd_data:
                if type(pre_fsd_data[item]) == objectLoader.ObjectLoader:
                    test = objstuff(pre_fsd_data[item])
                    fsd_list.append(test)

            return fsd_json
        
        elif type(pre_fsd_data) == objectLoader.ObjectLoader:
            test = "??"
            fsd_json=[]
            for item in pre_fsd_data.__dir__():
                #print(item)
                if item.startswith("__"):
                    continue
                else:
                    #print((item))
                    item2 = pre_fsd_data.__getattr__(item)
                    #fsd_json[str(fsd_file_path)].append(str(objstuff(item, test)))
                    if type(item2) == objectLoader.ObjectLoader:
                        #print(item2)
                        fsd_json.append(str(objstuff(item2, test)))
                        #print("??")
                    if type(item2) == dictLoader.DictLoader:
                        #print(item2)
                        fsd_json.append(str(dictstuff(item2, test)))
                        #print("??")
                    else:
                        fsd_json.append(str(item2))
                    #fsd_json[str(item)].append(item)


            #print(fsd_json)
                
            #fsd_list.append(fsd_json)
            

            return fsd_json
        elif type(pre_fsd_data) == dictLoader.IndexLoader:
            #print(list(pre_fsd_data.items()))
            fsd_json=[]
            test = "??"
            #fsd_json[str(fsd_file_path)].append(pre_fsd_data)
            #fsd_list.append(fsd_json)
            for item in (pre_fsd_data.items()):
                #print(item)
                for items in item:
                    #print(items)
                    if type(items) == objectLoader.ObjectLoader:
                        #print(item[items])
                        fsd_json.append({str(item): (objstuff(items, test))})
                        #print(items)
                    if type(items) == dictLoader.DictLoader:
                        #print(type(items))
                        fsd_json.append({str(item): ((dictstuff(items,test)))}) 
                    else:
                        #print(type(items))
                        fsd_json.append({str(item): str(items)})
            #print(fsd_json)
            #fsd_list.append(str(fsd_json))
            return fsd_json
        elif type(pre_fsd_data) == dictLoader.MultiIndexLoader:
            #print(list(pre_fsd_data.items()))
            fsd_json=[]
            fsd_json2=[]
            fsd_merged=[]
            test = "??"
            for item in pre_fsd_data.items():
                #fsd_json.append({"entry": item[0]})
                print(item[0])
                try:
                    for items in item:
                        #if type(items)==int:
                        #fsd_json.append({"entry": item[0], "values": str(items)})
                            #continue
                        #print (items.__dir__())
                        #print (type(items))
                        #fsd_json.append({"Entry": str(item[0]), "Values": str(items)})
                        if type(items) == objectLoader.ObjectLoader:
                            for items2 in items.__dir__():
                                #print(item[1])
                                if items2.startswith("__"):
                                    continue
                                else:
                                    #fsd_json.append({"entry": str(item[0])})
                                    testing = getattr(item[1],items2)
                                    #fsd_json.append({str(item[0]): str(items), str(items2): str(testing)})
                                    #print(getattr(items, items2))
                                    #print(testing)
                                    if type(testing) == dictLoader.DictLoader:
                                        #print(testing)
                                        try:
                                            #print(testing.schema['type'])
                                            #fsd_json.append({"entry": str(item[0]),  str(items2): ((dictstuff(testing)))})
                                            for items3 in testing:
                                                #print(type(testing))
                                                #print(items3)
                                                if type(testing) == objectLoader.ObjectLoader:
                                                    #print((testing[items3]))
                                                    fsd_json.append({"Entry": str(item[0]), str(items2): str(objstuff(testing), test)})
                                                    continue
                                                elif type(testing) == dictLoader.DictLoader:
                                                    #print("???????")
                                                    #fsd_json.append({"Entry": str(item[0]), str(items2): str((testing))})
                                                    for item4 in testing.items():
                                                        #print(items3)
                                                        fsd_json.append({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4)})
                                                        #print(item4)
                                                        for item5 in item4:
                                                            #print(type(item5))
                                                            if type(item5) == dictLoader.DictLoader:
                                                                for item6 in item5:
                                                                    #print(item6)
                                                                    fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item5.__getattr__(item6))}))
                                                            elif type(item5) == objectLoader.ObjectLoader:
                                                                #print(item5)
                                                                for item6 in item5.__dir__():
                                                                    #print(item6)
                                                                    if item6.startswith("__"):
                                                                        continue
                                                                    else:
                                                                        item7 = (item5.__getattr__(item6))
                                                                        if type(item7) == dictLoader.DictLoader:
                                                                            #print(item7)
                                                                            for item8 in item7:
                                                                                item9 = (item7[item8])
                                                                                #rint(str(item7.__getattr__(item8)))
                                                                                fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item8)}))
                                                                                if type(item9) == objectLoader.ObjectLoader:
                                                                                    #print(objstuff(item9))
                                                                                    for item10 in item9.__dir__():
                                                                                        if item10.startswith("__"):
                                                                                            continue
                                                                                        else:
                                                                                            item11 = (item9.__getattr__(item10))
                                                                                            if type(item11) == dictLoader.DictLoader:
                                                                                                item12 = (dictstuff(item11,test))
                                                                                                fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item8), str(item8): str(item9), str(item9): str(item10), str(item10): str(item11), str(item11): str(item12)}))
                                                                                            elif type(item11) == miscLoaders.VectorLoader:
                                                                                                fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item8), str(item8): str(item9), str(item9): str(item10), str(item10): str(item11.data)}))    
                                                                                            else:
                                                                                                fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item8), str(item8): str(item9), str(item9): str(item10)}))
                                                                                elif type(item9) == miscLoaders.VectorLoader:
                                                                                    fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item8), str(item8): str(item9.data)}))
                                                                                else:
                                                                                    fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item8), str(item8): str((item9))}))     
                                                                        elif type(item7) == miscLoaders.VectorLoader:
                                                                            #print(item7.data)
                                                                            fsd_json.append({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str("vectordata"), str("vectors for item : "): str(item7.data)})
                                                                                    
                                                                        else:
                                                                            fsd_json.append(({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(item4), str(item5): str(item6), str(item6): str(item7)}))
                                                            else:
                                                                #rint("?")
                                                                fsd_json.append({"Entry": str(item[0]), str(items2): str((testing)), str(item4): str(item5)})
                                                elif type(testing) == miscLoaders.VectorLoader:
                                                    #print("?")
                                                    fsd_json.append({"Entry": str(item[0]), str(items2): str(items3), str(items3): str(testing.data)})
                                                    
                                                else:
                                                    fsd_json.append({"Entry": str(item[0]), str(items2): str(items3)})
                                                    
                                        except:
                                            fsd_json.append({"Entry": str(item[0]), str(items2): str(dictstuff(testing,test))})
                                            
                                    elif type(testing) == miscLoaders.VectorLoader:
                                        #print(">")
                                        fsd_json.append({"Entry": str(item[0]), str(items2): str(vectorstuff(testing,test))})
                                        
                                    elif type(testing) == objectLoader.ObjectLoader:
                                        #print(testing)
                                        try:
                                            for items3 in testing.__dir__():
                                                if items3.startswith("__"):
                                                    continue
                                                else:
                                                    #print(type(objstuff(getattr(testing,items3))))
                                                    fsd_json.append({"Entry": str(item[0]), str(items2): str(objstuff(getattr(testing,items3),test))})
                                                    
                                        except:
                                            print("?2")
                                            fsd_json.append({"Entry": str(item[0]), str(items2): str(objstuff(testing,test))})
                                            
                                    else:
                                        #print(items2)
                                        fsd_json.append({"Entry": str(item[0]), str(items2): str(testing)})
                                        
                        elif type(items) == dictLoader.DictLoader:
                            print("??")
                    #fsd_json.append({"entry": item[0]})
                except:
                    raise
                    #fsd_json.append((items))
                    #print(fsd_json)
                #fsd_json2.insert(item[0], str(item[1]))
            return((fsd_json))


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
            return (fsd_list)
            
                
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
