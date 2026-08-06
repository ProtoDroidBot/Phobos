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


"""Incremental JSON writer for moons extracted from planet records."""


from .streaming_dict_writer import _StreamingDictWriter


class MoonsWriter(_StreamingDictWriter):
    """Create an atomic, incrementally written ``moons.json`` file."""

    def __init__(self, base_folder, translator, indent=2):
        super().__init__(
            base_folder=base_folder,
            translator=translator,
            entity_name='moon',
            indent=indent)
