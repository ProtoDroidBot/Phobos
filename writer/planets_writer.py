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


"""Incremental writer for planets and their nested moon index."""


from .streaming_dict_writer import (
    _CoordinatedMappingStreams,
    _StreamingDictWriter,
)


class PlanetsWriter(_StreamingDictWriter):
    """Create ``planets.json``, optionally cascading into ``moons.json``."""

    def __init__(self, base_folder, translator, indent=2, moons_writer=None):
        super().__init__(
            base_folder=base_folder,
            translator=translator,
            entity_name='planet',
            indent=indent)
        self._moons_writer = moons_writer

    def stream(self, miner_name, container_name, language, normalizer):
        if self._moons_writer is None:
            return super().stream(
                miner_name=miner_name,
                container_name=container_name,
                language=language,
                normalizer=normalizer)

        moon_stream = self._moons_writer.stream(
            miner_name=miner_name,
            container_name='moons',
            language=language,
            normalizer=normalizer)
        planet_stream = self._new_stream(
            miner_name=miner_name,
            container_name=container_name,
            language=language,
            normalizer=normalizer,
            field_handlers={
                'moon': moon_stream.write_mapping,
                'moons': moon_stream.write_mapping,
            })
        return _CoordinatedMappingStreams(
            streams=(moon_stream, planet_stream),
            exposed_stream=planet_stream)
