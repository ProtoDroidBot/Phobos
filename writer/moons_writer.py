"""Incremental JSON writer for moons extracted from planet records."""

from .streaming_dict_writer import _StreamingDictWriter


class MoonsWriter(_StreamingDictWriter):

    def __init__(self, base_folder, translator, indent=2):
        _StreamingDictWriter.__init__(
            self,
            base_folder=base_folder,
            translator=translator,
            entity_name='moon',
            indent=indent)
