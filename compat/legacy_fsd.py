"""Python 3 reader for the optimized FSD format used by Python 2 EVE clients.

This module implements only the runtime data-reading surface needed by Phobos.
It intentionally does not import or execute modules extracted from ``code.ccp``.
"""

from __future__ import annotations

import collections
import os
import struct

from .pickle_compat import restricted_loads


U8 = struct.Struct("<B")
U16 = struct.Struct("<H")
U32 = struct.Struct("<I")
I32 = struct.Struct("<i")
U64 = struct.Struct("<Q")
F32 = struct.Struct("<f")
F64 = struct.Struct("<d")
V2F = struct.Struct("<ff")
V2D = struct.Struct("<dd")
V3F = struct.Struct("<fff")
V3D = struct.Struct("<ddd")
V4F = struct.Struct("<ffff")
V4D = struct.Struct("<dddd")
KEY_OFFSET = struct.Struct("<ii")
KEY_OFFSET_SIZE = struct.Struct("<iii")


class LegacyFsdError(Exception):
    pass


class FsdPath:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent

    def __str__(self):
        if self.parent is None:
            return self.name
        return str(self.parent) + self.name


def _u32(data, offset=0):
    return U32.unpack_from(data, offset)[0]


def _read_u32(stream, offset):
    stream.seek(offset)
    value = stream.read(4)
    if len(value) != 4:
        raise LegacyFsdError("unable to read uint32 at offset {}".format(offset))
    return U32.unpack(value)[0]


def _read_at(stream, offset, size):
    stream.seek(offset)
    value = stream.read(size)
    if len(value) != size:
        raise LegacyFsdError("unable to read {} bytes at offset {}".format(size, offset))
    return value


def _decode_string(raw):
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


class VectorValue:
    def __init__(self, schema, values):
        self.schema = schema
        self.data = values

    def __getitem__(self, key):
        aliases = self.schema.get("aliases", {})
        if key in aliases:
            key = aliases[key]
        return self.data[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except (IndexError, KeyError) as error:
            raise AttributeError(str(error))


class LoaderState:
    def represent(self, data, offset, path, schema):
        try:
            factory = self.factories[schema["type"]]
        except KeyError:
            raise LegacyFsdError("unsupported FSD schema type {!r} at {}".format(schema.get("type"), path))
        return factory(data, offset, schema, path, self)

    @staticmethod
    def format_size(value):
        for suffix in ("bytes", "KB", "MB", "GB"):
            if abs(value) < 1024.0:
                return "{:.1f} {}".format(value, suffix)
            value /= 1024.0
        return "{:.1f} TB".format(value)


def _vector_factory(count):
    single_struct = {2: V2F, 3: V3F, 4: V4F}[count]
    double_struct = {2: V2D, 3: V3D, 4: V4D}[count]

    def load(data, offset, schema, path, state):
        unpacker = single_struct if schema.get("precision", "single") == "single" else double_struct
        values = unpacker.unpack_from(data, offset)
        if "aliases" in schema:
            return VectorValue(schema, values)
        return values

    return load


def _string(data, offset, schema, path, state):
    size = _u32(data, offset)
    return _decode_string(bytes(data[offset + 4 : offset + 4 + size]))


def _unicode(data, offset, schema, path, state):
    size = _u32(data, offset)
    return bytes(data[offset + 4 : offset + 4 + size]).decode("utf-8")


def _enum(data, offset, schema, path, state):
    values = schema.get("values", {})
    max_value = schema.get("maxEnumValue")
    if max_value is None:
        max_value = max(values.values()) if values else 0
    if max_value <= 255:
        value = U8.unpack_from(data, offset)[0]
    elif max_value <= 65536:
        value = U16.unpack_from(data, offset)[0]
    else:
        value = U32.unpack_from(data, offset)[0]
    if schema.get("readEnumValue", False):
        return value
    for key, candidate in values.items():
        if candidate == value:
            return key
    return None


def _bool(data, offset, schema, path, state):
    return U8.unpack_from(data, offset)[0] == 255


def _integer(data, offset, schema, path, state):
    unsigned = ("min" in schema and schema["min"] >= 0) or (
        "exclusiveMin" in schema and schema["exclusiveMin"] >= -1
    )
    return (U32 if unsigned else I32).unpack_from(data, offset)[0]


def _float(data, offset, schema, path, state):
    return (F64 if schema.get("precision", "single") == "double" else F32).unpack_from(data, offset)[0]


def _union(data, offset, schema, path, state):
    type_index = _u32(data, offset)
    return state.represent(data, offset + 4, path, schema["optionTypes"][type_index])


class FsdObject:
    def __init__(self, data, offset, schema, path, state):
        self.data = data
        self.offset = offset
        self.schema = schema
        self.path = path
        self.state = state
        self.variable_offsets = {}
        self.variable_base = None
        if "size" not in schema:
            optional_lookups = dict(schema.get("optionalValueLookups", {}))
            variable_attributes = []
            if optional_lookups:
                field = U64.unpack_from(data, offset + schema["endOfFixedSizeData"])[0]
                for name in schema["attributesWithVariableOffsets"]:
                    mask = optional_lookups.get(name)
                    if mask is None or field & mask:
                        variable_attributes.append(name)
            else:
                variable_attributes = list(schema.get("attributesWithVariableOffsets", ()))
            table_start = offset + schema.get("endOfFixedSizeData", 0) + 8
            table_size = 4 * len(variable_attributes)
            self.variable_base = table_start + table_size
            if variable_attributes:
                offsets = struct.unpack_from("<{}I".format(len(variable_attributes)), data, table_start)
                self.variable_offsets.update(zip(variable_attributes, offsets))

    def __getitem__(self, key):
        try:
            attribute_schema = self.schema["attributes"][key]
        except KeyError:
            raise KeyError("attribute {!r} is not in {}".format(key, self.path))
        fixed_offsets = self.schema.get("constantAttributeOffsets", {})
        child_path = FsdPath(".{}".format(key), parent=self.path)
        if key in fixed_offsets:
            return self.state.represent(self.data, self.offset + fixed_offsets[key], child_path, attribute_schema)
        if key not in self.variable_offsets:
            if "default" in attribute_schema:
                return attribute_schema["default"]
            raise KeyError("attribute {!r} is not present in {}".format(key, self.path))
        return self.state.represent(
            self.data,
            self.variable_base + self.variable_offsets[key],
            child_path,
            attribute_schema,
        )

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(str(error))

    def present_items(self):
        for name, schema in self.schema["attributes"].items():
            try:
                yield name, self[name]
            except KeyError:
                if "isOptional" not in schema:
                    raise

    def __repr__(self):
        return "<FSD Object: {}>".format(self.path)


def _object(data, offset, schema, path, state):
    return FsdObject(data, offset, schema, path, state)


def _list(data, offset, schema, path, state, known_length=None):
    known_length = schema.get("length", known_length)
    fixed_length = known_length is not None
    count = known_length if fixed_length else _u32(data, offset)
    count_offset = 0 if fixed_length else 4
    item_schema = schema["itemTypes"]
    result = []
    if "fixedItemSize" in schema:
        item_size = item_schema["size"]
        for index in range(count):
            item_offset = offset + count_offset + item_size * index
            result.append(state.represent(data, item_offset, FsdPath("[{}]".format(index), path), item_schema))
    else:
        for index in range(count):
            relative_offset = _u32(data, offset + count_offset + 4 * index)
            result.append(
                state.represent(data, offset + relative_offset, FsdPath("[{}]".format(index), path), item_schema)
            )
    return result


class OptimizedFooter:
    def __init__(self, data, schema):
        attributes = schema["keyFooter"]["itemTypes"]["attributes"]
        self.unpacker = KEY_OFFSET_SIZE if "size" in attributes else KEY_OFFSET
        self.has_size = self.unpacker is KEY_OFFSET_SIZE
        self.data = data
        self.count = _u32(data, 0)
        self.start = 4

    def get(self, key):
        low = 0
        high = self.count - 1
        while low <= high:
            middle = (low + high) // 2
            current = self._unpack(middle)
            if current[0] < key:
                low = middle + 1
            elif current[0] > key:
                high = middle - 1
            else:
                return current[1], current[2]
        return None

    def _unpack(self, index):
        values = self.unpacker.unpack_from(self.data, self.start + index * self.unpacker.size)
        if self.has_size:
            return values
        return values[0], values[1], 0

    def items(self):
        for index in range(self.count):
            key, offset, size = self._unpack(index)
            yield key, (offset, size)

    def __len__(self):
        return self.count


class GenericFooter:
    def __init__(self, data, schema, path, state):
        self.values = _list(data, 0, schema["keyFooter"], FsdPath("<keyFooter>", path), state)

    def get(self, key):
        low = 0
        high = len(self.values) - 1
        while low <= high:
            middle = (low + high) // 2
            item = self.values[middle]
            current = item["key"]
            if current < key:
                low = middle + 1
            elif current > key:
                high = middle - 1
            else:
                try:
                    size = item["size"]
                except KeyError:
                    size = 0
                return item["offset"], size
        return None

    def items(self):
        for item in self.values:
            try:
                size = item["size"]
            except KeyError:
                size = 0
            yield item["key"], (item["offset"], size)

    def __len__(self):
        return len(self.values)


def _create_footer(schema, data, path, state):
    if schema["keyTypes"]["type"] == "int":
        return OptimizedFooter(data, schema)
    return GenericFooter(data, schema, path, state)


class DictValue:
    def __init__(self, data, offset, schema, path, state):
        self.data = data
        self.offset = offset
        self.schema = schema
        self.path = path
        self.state = state
        size_of_data = _u32(data, offset)
        footer_size_offset = offset + 4 + size_of_data - 4
        footer_size = _u32(data, footer_size_offset)
        footer_start = offset + size_of_data - footer_size
        footer_data = data[footer_start : footer_start + footer_size]
        self.footer = _create_footer(schema, footer_data, path, state)

    def _value(self, key, relative_offset):
        return self.state.represent(
            self.data,
            self.offset + 4 + relative_offset,
            FsdPath("[{}]".format(key), self.path),
            self.schema["valueTypes"],
        )

    def __getitem__(self, key):
        found = self.footer.get(key)
        if found is None:
            raise KeyError(key)
        return self._value(key, found[0])

    def items(self):
        for key, (offset, unused_size) in self.footer.items():
            yield key, self._value(key, offset)

    def __iter__(self):
        for key, unused in self.footer.items():
            yield key

    def __len__(self):
        return len(self.footer)


def _dict(data, offset, schema, path, state):
    return DictValue(data, offset, schema, path, state)


class IndexValue:
    def __init__(self, stream, cache_size, schema, path, state, offset_to_data=0, offset_to_footer=0):
        self.stream = stream
        self.cache_size = cache_size
        self.schema = schema
        self.path = path
        self.state = state
        self.offset_to_data = offset_to_data
        file_size = _read_u32(stream, offset_to_data)
        footer_size_offset = offset_to_data + file_size
        if offset_to_footer:
            footer_size_offset = offset_to_footer - 4
        footer_size = _read_u32(stream, footer_size_offset)
        footer_start = footer_size_offset - footer_size
        footer_data = _read_at(stream, footer_start, footer_size)
        self.footer = _create_footer(schema, footer_data, path, state)
        self.cache = collections.OrderedDict()

    def _value(self, key, item_offset, item_size):
        offset = 4 + self.offset_to_data + item_offset
        value_schema = self.schema["valueTypes"]
        if value_schema.get("buildIndex", False):
            return IndexValue(
                self.stream,
                self.cache_size,
                value_schema,
                FsdPath("[{}]".format(key), self.path),
                self.state,
                offset_to_data=offset,
                offset_to_footer=offset + item_size,
            )
        raw = _read_at(self.stream, offset, item_size)
        return self.state.represent(raw, 0, FsdPath("[{}]".format(key), self.path), value_schema)

    def __getitem__(self, key):
        if key in self.cache:
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        found = self.footer.get(key)
        if found is None:
            raise KeyError(key)
        value = self._value(key, found[0], found[1])
        if len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)
        self.cache[key] = value
        return value

    def items(self):
        for key, (offset, size) in self.footer.items():
            yield key, self._value(key, offset, size)

    def __iter__(self):
        for key, unused in self.footer.items():
            yield key

    def __len__(self):
        return len(self.footer)


LoaderState.factories = {
    "float": _float,
    "vector4": _vector_factory(4),
    "color": _vector_factory(4),
    "vector3": _vector_factory(3),
    "vector2": _vector_factory(2),
    "string": _string,
    "resPath": _string,
    "unicode": _unicode,
    "enum": _enum,
    "bool": _bool,
    "int": _integer,
    "typeID": _integer,
    "localizationID": _integer,
    "union": _union,
    "list": _list,
    "object": _object,
    "dict": _dict,
    "npcTag": _integer,
    "deploymentType": _integer,
    "npcEnemyFleetTypeID": _integer,
    "groupBehaviorTreeID": _integer,
    "npcCorporationID": _integer,
    "spawnTableID": _integer,
    "npcFleetCounterTableID": _integer,
    "dungeonID": _integer,
    "fsdReference": _integer,
    "raceID": _integer,
    "marketGroupID": _integer,
    "ShipGroupID": _integer,
    "certificateTemplateID": _integer,
    "factionID": _integer,
}


def _load_yaml_schema(schema_path):
    try:
        import yaml
    except ImportError as error:
        raise LegacyFsdError(
            "PyYAML is required for external legacy FSD schemas; install requirements.txt"
        ) from error
    with open(schema_path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_legacy_fsd(data_path, schema_path=None, cache_size=100):
    """Load one legacy FSD ``.static`` file and return its lazy root value."""
    state = LoaderState()
    stream = open(data_path, "rb")
    try:
        offset_to_data = 0
        if schema_path is None:
            schema_size = _read_u32(stream, 0)
            schema_raw = _read_at(stream, 4, schema_size)
            schema = restricted_loads(schema_raw, encoding="latin-1")
            offset_to_data = schema_size + 4
        else:
            schema = _load_yaml_schema(schema_path)

        if schema.get("type") == "dict" and schema.get("buildIndex", False):
            root = IndexValue(stream, cache_size, schema, FsdPath("<{}>".format(data_path)), state, offset_to_data)
            root._owned_stream = stream
            stream = None
            return root

        if offset_to_data:
            stream.seek(0)
        raw = stream.read()
        return state.represent(raw, offset_to_data, FsdPath("<{}>".format(data_path)), schema)
    finally:
        if stream is not None:
            stream.close()


def materialize(value):
    """Convert lazy FSD values into built-in JSON-serializable structures."""
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    if isinstance(value, VectorValue):
        aliases = value.schema.get("aliases")
        if aliases:
            return {name: materialize(value.data[index]) for name, index in aliases.items()}
        return [materialize(item) for item in value.data]
    if isinstance(value, FsdObject):
        return {name: materialize(item) for name, item in value.present_items()}
    if isinstance(value, (DictValue, IndexValue)):
        try:
            return {materialize(key): materialize(item) for key, item in value.items()}
        finally:
            owned = getattr(value, "_owned_stream", None)
            if owned is not None:
                owned.close()
                value._owned_stream = None
    if isinstance(value, dict):
        return {materialize(key): materialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [materialize(item) for item in value]
    raise LegacyFsdError("unable to materialize {}".format(type(value)))


def load_and_materialize(data_path, schema_path=None, cache_size=100):
    return materialize(load_legacy_fsd(data_path, schema_path=schema_path, cache_size=cache_size))
