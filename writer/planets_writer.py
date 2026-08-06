"""Incremental writer for planets and their nested moon index."""

from .streaming_dict_writer import (
    _CoordinatedMappingStreams,
    _StreamingDictWriter,
)


class PlanetsWriter(_StreamingDictWriter):

    def __init__(self, base_folder, translator, indent=2, moons_writer=None):
        _StreamingDictWriter.__init__(
            self,
            base_folder=base_folder,
            translator=translator,
            entity_name='planet',
            indent=indent)
        self._moons_writer = moons_writer

    def stream(self, miner_name, container_name, language, normalizer):
        if self._moons_writer is None:
            return _StreamingDictWriter.stream(
                self,
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
