#!/usr/bin/env python3
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


import argparse
import os.path
import sys


REQUIRED_PYTHON = (3, 12)


def _python_version_error():
    major, minor = sys.version_info[:2]
    return 'Phobos requires Python 3.12, but {}.{} was used\n'.format(
        major, minor)


# Check before importing the rest of the application so an unsupported
# interpreter reports the actual requirement instead of an incidental import
# failure.
if __name__ == '__main__' and sys.version_info[:2] != REQUIRED_PYTHON:
    sys.stderr.write(_python_version_error())
    raise SystemExit(1)

from flow import FlowManager
from miner import (
    FsdBinaryMiner,
    FsdBuiltMiner,
    FsdLiteMiner,
    MetadataMiner,
    PickleMiner,
    SqliteMiner,
    TraitMiner,
)
from util import ResourceBrowser, Translator
from writer import JsonWriter, MoonsWriter, PlanetsWriter


def run(path_eve, server_alias, filter_string, language, path_json, group=None):
    resource_browser = ResourceBrowser(eve_path=path_eve, server_alias=server_alias)

    pickle_miner = PickleMiner(resbrowser=resource_browser)
    trans = Translator(pickle_miner=pickle_miner)
    moons_writer = MoonsWriter(path_json, translator=trans, indent=2)
    planets_writer = PlanetsWriter(
        path_json,
        translator=trans,
        indent=2,
        moons_writer=moons_writer,
    )
    fsdbinary_miner = FsdBinaryMiner(
        resbrowser=resource_browser,
        translator=trans,
        planets_writer=planets_writer,
    )
    fsdlite_miner = FsdLiteMiner(resbrowser=resource_browser, translator=trans)
    fsdbuilt_miner = FsdBuiltMiner(resbrowser=resource_browser, translator=trans)
    miners = [
        MetadataMiner(resbrowser=resource_browser),
        fsdbinary_miner,
        fsdlite_miner,
        fsdbuilt_miner,
        TraitMiner(fsdlite_miner=fsdlite_miner, fsdbuilt_miner=fsdbuilt_miner, translator=trans),
        SqliteMiner(resbrowser=resource_browser, translator=trans),
        pickle_miner]

    writers = [
        JsonWriter(path_json, indent=2, group=group)]

    FlowManager(miners, writers).run(filter_string=filter_string, language=language)


def build_parser():
    parser = argparse.ArgumentParser(description='This script extracts data from EVE client and writes it into JSON files')
    parser.add_argument('-e', '--eve', required=True,
                        help='Path to EVE client\'s folder')
    parser.add_argument('-s', '--server', default='stillness',
                        help='Server to pull data from. Default is "stillness"',
                        choices=('stillness', 'utopia'))
    parser.add_argument('-j', '--json', required=True,
                        help='Output folder for the JSON files')
    parser.add_argument('-t', '--translate', default='multi',
                        help='Attempt to translate strings into specified language. Default is "multi"',
                        choices=('de', 'en-us', 'es', 'fr', 'it', 'ja', 'ko', 'ru', 'zh', 'multi'))
    parser.add_argument('-l', '--list', default='',
                        help='Comma-separated list of container names to extract. If not specified, extracts everything')
    parser.add_argument('-g', '--group', type=int, default=None,
                        help='Split output into several files, containing this amount of top-level entities at most')
    return parser


def main(argv=None):
    if sys.version_info[:2] != REQUIRED_PYTHON:
        sys.stderr.write(_python_version_error())
        return 1

    args = build_parser().parse_args(argv)

    # Expand home directory
    path_eve = os.path.expanduser(args.eve)
    path_json = os.path.expanduser(args.json)

    run(path_eve=path_eve, server_alias=args.server, filter_string=args.list,
        language=args.translate, path_json=path_json, group=args.group)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
