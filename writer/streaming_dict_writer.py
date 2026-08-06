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


"""Shared machinery for incrementally writing indexed JSON dictionaries."""


import json
import os
import re
import tempfile

from .json_writer import CustomEncoder


class _StreamingDictWriter(object):
    """Factory for atomic streams of normalized, translated records."""

    def __init__(self, base_folder, translator, entity_name, indent=2):
        self.base_folder = base_folder
        self.translator = translator
        self.entity_name = entity_name
        self.indent = indent

    def stream(self, miner_name, container_name, language, normalizer):
        return self._new_stream(
            miner_name=miner_name,
            container_name=container_name,
            language=language,
            normalizer=normalizer)

    def _new_stream(
            self, miner_name, container_name, language, normalizer,
            field_handlers=None):
        return _AtomicMappingStream(
            base_folder=self.base_folder,
            translator=self.translator,
            entity_name=self.entity_name,
            indent=self.indent,
            miner_name=miner_name,
            container_name=container_name,
            language=language,
            normalizer=normalizer,
            field_handlers=field_handlers)


class _AtomicMappingStream(object):

    def __init__(self, base_folder, translator, entity_name, indent,
                 miner_name, container_name, language, normalizer,
                 field_handlers=None):
        folder = os.path.join(base_folder, _secure_name(miner_name))
        filename = u'{}.json'.format(_secure_name(container_name))

        self._folder = folder
        self._filepath = os.path.join(folder, filename)
        self._temp_prefix = u'.{}.'.format(filename)
        self._translator = translator
        self._entity_name = entity_name
        self._language = language
        self._normalizer = normalizer
        self._field_handlers = field_handlers
        self._indent = indent
        self._indent_text = _indent_text(indent)
        self._encoder = CustomEncoder(
            ensure_ascii=False,
            indent=indent,
            sort_keys=False)

        self._file = None
        self._temp_path = None
        self._first_entry = True
        self._seen_ids = set()
        self._started = False
        self._prepared = False
        self._committed = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.abort()
            return False
        try:
            self.prepare()
            _commit_stream_group((self,))
        except BaseException:
            self.abort()
            raise
        return False

    def open(self):
        if self._started:
            raise RuntimeError(
                '{} stream has already been opened'.format(
                    self._entity_name))
        self._started = True

        os.makedirs(self._folder, mode=0o755, exist_ok=True)
        descriptor, self._temp_path = tempfile.mkstemp(
            dir=self._folder,
            prefix=self._temp_prefix,
            suffix='.tmp',
            text=True)
        try:
            self._file = os.fdopen(
                descriptor, 'w', encoding='utf-8', newline='\n')
            self._file.write('{')
        except BaseException:
            if self._file is None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            self.abort()
            raise

    def prepare(self):
        if self._file is None:
            raise RuntimeError(
                '{} stream is not open'.format(self._entity_name))
        output = self._file
        try:
            if not self._first_entry and self._indent is not None:
                output.write('\n')
            output.write('}')
            output.flush()
            os.fsync(output.fileno())
        finally:
            self._file = None
            output.close()
        self._prepared = True

    def abort(self):
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
        if self._temp_path is not None:
            try:
                os.unlink(self._temp_path)
            except FileNotFoundError:
                pass
            self._temp_path = None

    def write_mapping(self, raw_mapping):
        """Stream a mapping and return its normalized numeric IDs."""
        if self._file is None or self._prepared:
            raise RuntimeError(
                '{} stream is not open'.format(self._entity_name))

        try:
            items = raw_mapping.items()
        except AttributeError as error:
            raise TypeError(
                '{} data must provide a mapping interface'.format(
                    self._entity_name)) from error

        record_ids = []
        for raw_record_id, raw_record in items:
            record_id = self._normalizer(raw_record_id)
            self._validate_record_id(record_id)
            if record_id in self._seen_ids:
                raise ValueError(
                    'duplicate {} ID {!r}'.format(
                        self._entity_name, record_id))

            if self._field_handlers is None:
                record = self._normalizer(raw_record)
            else:
                record = self._normalizer(
                    raw_record, field_handlers=self._field_handlers)
            if not isinstance(record, dict):
                raise TypeError(
                    '{} {!r} normalized to {}, expected dict'.format(
                        self._entity_name, record_id,
                        type(record).__name__))

            self._translator.translate_container(
                record, self._language, verbose=False)
            self._write_entry(record_id, record)
            self._seen_ids.add(record_id)
            record_ids.append(record_id)

        return record_ids

    def _validate_record_id(self, record_id):
        if isinstance(record_id, bool) or not isinstance(record_id, int):
            raise TypeError(
                '{} ID must normalize to an integer other than bool, '
                'got {!r}'.format(self._entity_name, record_id))

    def _write_entry(self, record_id, record):
        if self._first_entry:
            separator = '\n' if self._indent is not None else ''
        else:
            separator = ',\n' if self._indent is not None else ','
        self._file.write(separator)

        if self._indent is not None:
            self._file.write(self._indent_text)
        self._file.write(json.dumps(str(record_id), ensure_ascii=False))
        self._file.write(': ' if self._indent is not None else ':')

        for chunk in self._encoder.iterencode(record):
            if self._indent is not None and '\n' in chunk:
                chunk = chunk.replace('\n', '\n' + self._indent_text)
            self._file.write(chunk)
        self._first_entry = False

    def _mark_committed(self):
        self._temp_path = None
        self._committed = True


class _CoordinatedMappingStreams(object):
    """Use several mapping streams as one ordinary context manager."""

    def __init__(self, streams, exposed_stream):
        self._streams = tuple(streams)
        self._exposed_stream = exposed_stream
        self._opened = False

    def __enter__(self):
        opened = []
        try:
            for stream in self._streams:
                stream.open()
                opened.append(stream)
        except BaseException:
            for stream in reversed(opened):
                stream.abort()
            raise
        self._opened = True
        return self._exposed_stream

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._opened:
            return False
        if exc_type is not None:
            for stream in reversed(self._streams):
                stream.abort()
            return False
        try:
            for stream in self._streams:
                stream.prepare()
            _commit_stream_group(self._streams)
        except BaseException:
            for stream in reversed(self._streams):
                stream.abort()
            raise
        return False


def _commit_stream_group(streams):
    """Promote prepared streams together, restoring old files on failure."""
    streams = tuple(streams)
    for stream in streams:
        if not stream._prepared or stream._temp_path is None:
            raise RuntimeError('cannot commit an unprepared JSON stream')

    backups = {}
    promoted = []
    try:
        for stream in streams:
            if os.path.lexists(stream._filepath):
                backup_path = _reserve_backup_path(
                    stream._folder,
                    os.path.basename(stream._filepath))
                os.replace(stream._filepath, backup_path)
                backups[stream] = backup_path

        for stream in streams:
            os.replace(stream._temp_path, stream._filepath)
            promoted.append(stream)
    except BaseException as error:
        rollback_errors = []
        for stream in reversed(promoted):
            if stream in backups:
                continue
            try:
                os.unlink(stream._filepath)
            except FileNotFoundError:
                pass
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        for stream in reversed(streams):
            backup_path = backups.get(stream)
            if backup_path is None:
                continue
            try:
                os.replace(backup_path, stream._filepath)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors and hasattr(error, 'add_note'):
            error.add_note(
                'unable to completely roll back JSON outputs: {}'.format(
                    '; '.join(str(item) for item in rollback_errors)))
        raise

    for stream in streams:
        stream._mark_committed()
    for backup_path in backups.values():
        try:
            os.unlink(backup_path)
        except FileNotFoundError:
            pass
        except OSError:
            # Both requested outputs are already committed. A stale hidden
            # backup is safer than undoing successfully promoted files.
            pass


def _reserve_backup_path(folder, filename):
    descriptor, backup_path = tempfile.mkstemp(
        dir=folder,
        prefix=u'.{}.'.format(filename),
        suffix='.bak')
    os.close(descriptor)
    try:
        os.unlink(backup_path)
    except BaseException:
        try:
            os.unlink(backup_path)
        except OSError:
            pass
        raise
    return backup_path


def _indent_text(indent):
    if indent is None:
        return ''
    if isinstance(indent, str):
        return indent
    if isinstance(indent, int):
        return ' ' * max(0, indent)
    raise TypeError('indent must be None, an integer, or a string')


def _secure_name(name):
    return re.sub(r'[^\w\-.,() ]', '_', name, flags=re.UNICODE)
