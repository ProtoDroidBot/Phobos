#!/usr/bin/env python
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


import os
import sys

from flow import FlowManager
from miner import *
from writer import *
from util import ResourceBrowser, Translator
from compat import ExtractionManifest, detect_client_profile
from compat.native_worker import NativeWorker, find_legacy_code_root, find_python2
from compat.legacy_runtime import prepare_legacy_runtime


def run(
        path_eve,
        server_alias,
        filter_string,
        language,
        path_json,
        group=None,
        client_runtime='auto',
        python2_executable=None,
        legacy_code_root=None,
        strict=False,
        manifest_name='_phobos_manifest.json'):
    client_profile = detect_client_profile(path_eve, server_alias, runtime_override=client_runtime)
    print('Client build {}: runtime {}'.format(client_profile.build, client_profile.runtime))
    resource_browser = ResourceBrowser(eve_path=path_eve, server_alias=server_alias)

    native_worker = None
    if client_profile.is_legacy_py27:
        python2_path = find_python2(python2_executable)
        if legacy_code_root:
            legacy_code_path = find_legacy_code_root(client_profile.build, legacy_code_root)
        elif client_profile.code_ccp_path:
            legacy_code_path = prepare_legacy_runtime(client_profile.code_ccp_path, client_profile.build)
        else:
            legacy_code_path = None
        native_worker = NativeWorker(
            python2_executable=python2_path,
            client_bin64=os.path.join(path_eve, server_alias, 'bin64'),
            legacy_code_root=legacy_code_path,
        )
        if not native_worker.available:
            print('Python 2 native worker is unavailable; pure Python 3 legacy miners will still run')

    pickle_miner = PickleMiner(resbrowser=resource_browser)
    trans = Translator(pickle_miner=pickle_miner)
    fsdlite_miner = FsdLiteMiner(resbrowser=resource_browser, translator=trans)
    fsdbuilt_miner = FsdBuiltMiner(
        resbrowser=resource_browser,
        translator=trans,
        client_profile=client_profile,
        native_worker=native_worker,
    )
    fsdbin_miner = FsdBinaryMiner(
        resbrowser=resource_browser,
        translator=trans,
        client_profile=client_profile,
    )
    miners = [
        MetadataMiner(resbrowser=resource_browser),
        fsdbin_miner,
        fsdlite_miner,
        fsdbuilt_miner,
        # Traits do not exist yet on EVE Frontier. :(
        #TraitMiner(fsdlite_miner=fsdlite_miner, fsdbuilt_miner=fsdbuilt_miner, translator=trans),
        SqliteMiner(resbrowser=resource_browser, translator=trans),
        pickle_miner]

    writers = [
        JsonWriter(path_json, indent=2, group=group)]

    manifest = ExtractionManifest(client_profile)
    FlowManager(miners, writers, manifest=manifest).run(filter_string=filter_string, language=language)
    manifest_path = manifest.write(path_json, filename=manifest_name)
    print('Extraction manifest: {}'.format(manifest_path))
    if strict and manifest.failures:
        raise RuntimeError('{} containers failed; see {}'.format(len(manifest.failures), manifest_path))
    return manifest


if __name__ == '__main__':

    try:
        major = sys.version_info.major
        minor = sys.version_info.minor
    except AttributeError:
        major = sys.version_info[0]
        minor = sys.version_info[1]
    if major != 3 or minor != 12:
        sys.stderr.write('This application requires Python 3.12 to run, but {0}.{1} was used\n'.format(major, minor))
        sys.exit()

    import argparse
    import os.path

    parser = argparse.ArgumentParser(description='This script extracts data from EVE client and writes it into JSON files')
    parser.add_argument('-e', '--eve', required=True,
                        help='Path to EVE client\'s folder')
    parser.add_argument('-s', '--server', default='stillness',
                        help='Server to pull data from. Default is "stillness"',
                        choices=('stillness', 'tq'))
    parser.add_argument('-j', '--json', required=True,
                        help='Output folder for the JSON files')
    parser.add_argument('-t', '--translate', default='multi',
                        help='Attempt to translate strings into specified language. Default is "multi"',
                        choices=('de', 'en-us', 'es', 'fr', 'it', 'ja', 'ru', 'zh', 'multi'))
    parser.add_argument('-l', '--list', default='',
                        help='Comma-separated list of container names to extract. If not specified, extracts everything')
    parser.add_argument('-g', '--group', type=int, default=None,
                        help='Split output into several files, containing this amount of top-level entities at most')
    parser.add_argument('--client-runtime', default='auto',
                        choices=('auto', 'python3', 'legacy_py27'),
                        help='Override automatic EVE client runtime detection')
    parser.add_argument('--python2', default=None,
                        help='Path to a 64-bit Python 2.7 interpreter for legacy native loaders')
    parser.add_argument('--legacy-code-root', default=None,
                        help='Executable Python 2 import tree; normally generated automatically from code.ccp')
    parser.add_argument('--strict', action='store_true',
                        help='Exit with an error if any requested container fails')
    parser.add_argument('--manifest-name', default='_phobos_manifest.json',
                        help='Filename for the extraction manifest')
    args = parser.parse_args()

    # Expand home directory
    path_eve = os.path.expanduser(args.eve)
    path_json = os.path.expanduser(args.json)

    run(path_eve=path_eve, server_alias=args.server, filter_string=args.list, language=args.translate,
        path_json=path_json, group=args.group, client_runtime=args.client_runtime,
        python2_executable=args.python2, legacy_code_root=args.legacy_code_root,
        strict=args.strict, manifest_name=args.manifest_name)
