"""Shared Python 2.7 machinery for streamed indexed JSON dictionaries."""

import codecs
import ctypes
import errno
import json
import os
import re
import sys
import tempfile

from .json_writer import CustomEncoder


class _StreamingDictWriter(object):

    def __init__(self, base_folder, translator, entity_name, indent=2):
        self.base_folder = _unicode_path(base_folder)
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

        try:
            os.makedirs(self._folder, mode=0o755)
        except OSError as error:
            if error.errno != errno.EEXIST or not os.path.isdir(self._folder):
                raise

        descriptor, self._temp_path = tempfile.mkstemp(
            dir=self._folder,
            prefix=self._temp_prefix,
            suffix=u'.tmp',
            text=True)
        os.close(descriptor)
        try:
            self._file = codecs.open(
                self._temp_path, mode='wb', encoding='utf-8')
            self._file.write(u'{')
        except BaseException:
            self.abort()
            raise

    def prepare(self):
        if self._file is None:
            raise RuntimeError(
                '{} stream is not open'.format(self._entity_name))
        output = self._file
        try:
            if not self._first_entry and self._indent is not None:
                output.write(u'\n')
            output.write(u'}')
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
            except (IOError, OSError):
                pass
            self._file = None
        if self._temp_path is not None:
            _remove_if_exists(self._temp_path)
            self._temp_path = None

    def write_mapping(self, raw_mapping):
        """Stream a mapping and return its normalized numeric IDs."""
        if self._file is None or self._prepared:
            raise RuntimeError(
                '{} stream is not open'.format(self._entity_name))

        items_method = getattr(raw_mapping, 'iteritems', None)
        if items_method is None:
            items_method = getattr(raw_mapping, 'items', None)
        if items_method is None:
            raise TypeError(
                '{} data must provide a mapping interface'.format(
                    self._entity_name))

        record_ids = []
        for raw_record_id, raw_record in items_method():
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
        if (
            isinstance(record_id, bool) or
            not isinstance(record_id, (int, long))
        ):
            raise TypeError(
                '{} ID must normalize to an integer other than bool, '
                'got {!r}'.format(self._entity_name, record_id))

    def _write_entry(self, record_id, record):
        if self._first_entry:
            separator = u'\n' if self._indent is not None else u''
        else:
            separator = u',\n' if self._indent is not None else u','
        self._file.write(separator)

        if self._indent is not None:
            self._file.write(self._indent_text)
        self._file.write(json.dumps(unicode(record_id), ensure_ascii=False))
        self._file.write(u': ' if self._indent is not None else u':')

        for chunk in self._encoder.iterencode(record):
            if not isinstance(chunk, unicode):
                chunk = chunk.decode('utf-8')
            if self._indent is not None and u'\n' in chunk:
                chunk = chunk.replace(u'\n', u'\n' + self._indent_text)
            self._file.write(chunk)
        self._first_entry = False

    def _mark_committed(self):
        self._temp_path = None


class _CoordinatedMappingStreams(object):

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
                try:
                    _replace_file(stream._filepath, backup_path)
                except BaseException:
                    _remove_if_exists(backup_path)
                    raise
                backups[stream] = backup_path

        for stream in streams:
            _replace_file(stream._temp_path, stream._filepath)
            promoted.append(stream)
    except BaseException as error:
        rollback_errors = []
        for stream in reversed(promoted):
            if stream not in backups:
                try:
                    os.unlink(stream._filepath)
                except OSError as rollback_error:
                    if rollback_error.errno != errno.ENOENT:
                        rollback_errors.append(
                            'unable to remove newly promoted {!r}: {}'.format(
                                stream._filepath, rollback_error))
        for stream in reversed(streams):
            backup_path = backups.get(stream)
            if backup_path is None:
                continue
            try:
                _replace_file(backup_path, stream._filepath)
            except (IOError, OSError) as rollback_error:
                rollback_errors.append(
                    'unable to restore {!r} from retained backup {!r}: {}'.format(
                        stream._filepath, backup_path, rollback_error))
        if rollback_errors:
            raise RuntimeError(
                'JSON stream promotion failed ({}: {}) and rollback was '
                'incomplete: {}'.format(
                    type(error).__name__, error,
                    '; '.join(rollback_errors)))
        raise

    for stream in streams:
        stream._mark_committed()
    for backup_path in backups.values():
        _remove_if_exists(backup_path)


def _replace_file(source, destination):
    """Atomically replace ``destination`` with ``source`` on Python 2.7."""
    if os.name != 'nt':
        os.rename(source, destination)
        return

    move_file_ex = ctypes.windll.kernel32.MoveFileExW
    move_file_ex.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint)
    move_file_ex.restype = ctypes.c_int
    flags = 0x1 | 0x8  # MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
    if not move_file_ex(
            _unicode_path(source), _unicode_path(destination), flags):
        raise ctypes.WinError()


def _reserve_backup_path(folder, filename):
    descriptor, backup_path = tempfile.mkstemp(
        dir=folder,
        prefix=u'.{}.'.format(filename),
        suffix=u'.bak')
    os.close(descriptor)
    return backup_path


def _remove_if_exists(path):
    try:
        os.unlink(path)
    except OSError as error:
        if error.errno != errno.ENOENT:
            # Cleanup is best-effort so it never hides the extraction error.
            pass


def _indent_text(indent):
    if indent is None:
        return u''
    if isinstance(indent, (int, long)):
        return u' ' * max(0, indent)
    raise TypeError('indent must be None or an integer on Python 2.7')


def _secure_name(name):
    if not isinstance(name, unicode):
        name = name.decode('utf-8')
    return re.sub(ur'[^\w\-.,() ]', u'_', name, flags=re.UNICODE)


def _unicode_path(path):
    if isinstance(path, unicode):
        return path
    encoding = sys.getfilesystemencoding() or 'mbcs'
    return path.decode(encoding)
