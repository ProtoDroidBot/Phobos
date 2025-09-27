# AI Coding Agent Instructions for Phobos

This document gives AI assistants the minimum project-specific knowledge to be productive. Keep answers concrete, cite file paths, follow existing patterns, prefer small focused changes.

## 1. Purpose & Big Picture
Phobos (see `README.md`) extracts EVE Online and EVE Frontier client data and emits normalized JSON datasets. Core flow: miners enumerate container names -> each container's raw client data is loaded, normalized, optionally localized, then written by writers (currently JSON only) into `output/<miner_name>/*.json`.

High-level components:
- Miners (`miner/`): Read different on-disk formats (SQLite, FSDLite, FSD built binary via dynamic loader, resource pickles, raw staticdata, constructed traits, metadata). Each subclass of `BaseMiner` exposes `contname_iter()` and `get_data(container_name, ...)`.
- Resource access (`util/resource_browser.py`): Discovers and integrity-verifies EVE client resources using CCP index files. All miners rely on this to resolve resource paths like `res:/staticdata/...` or `app:/bin64/...`.
- Localization (`util/translator.py`): Post-process pass that walks arbitrary nested dict/list/tuple structures, replacing `fieldName` values based on `fieldNameID` + language selection. Supports single language in-place or multi-language (`--translate=multi`) which appends `<field>_<lang>` fields.
- Normalization (`util/eve_normalize.py`): Converts proprietary FSD loader objects (and other Eve-specific container/iterator classes) into pure Python primitives before translation / serialization.
- Writers (`writer/`): Serialize miner output. `JsonWriter` groups or sorts data deterministically.
- Flow orchestration (`flow.py` + `run.py`): Builds miners/writers list, parses CLI, filters requested containers, invokes translation & write pipeline.

## 2. Runtime & Environment Constraints
- Requires Python 3.12 exactly (see version gate in `run.py`). FSD built miner (`FsdBuiltMiner`) additionally requires 64-bit Windows (`os.name == 'nt'` and pointer size 64) because it imports `.pyd` loaders under `app:/bin64/`.
- No dependency manifest present; project currently uses only Python stdlib.
- Dangerous operations: executing untrusted pickles (see `PickleMiner`) and dynamic C extension loaders (see README safety note). Suggest sandboxing if adding new execution paths.

## 3. Typical Invocation
From repo root:
```
python run.py --eve "C:\\CCP\\EVE Online" --json output --translate=multi --list="metadata,traits"
```
Filter string parsing allows commas and parentheses (see `FlowManager._parse_filter`). Empty `--list` means "dump everything".

## 4. Container Naming Conventions
- SQLite: `<resource_path_without_.db>_<tableName>` built dynamically (`SqliteMiner._contname_dbtable_map`).
- FSDLite: resource paths `res:/staticdata/*.static` become `<fname>` (strip extension) if file is an SQLite DB with a `cache` table.
- FSD Built: Match loader `app:/bin64/...<name>Loader.pyd` with data `res:/staticdata/...<name>.fsdbinary` -> container name `<name>` (lowercased). Output is normalized dict structures.
- FSD Binary+Schema (experimental `FsdBinaryMiner`): Consumes `.static` + optional matching `.schema`; returns deeply nested diagnostic expansion of loader object graph (not normalized) — recursive helpers `dictstuff/objstuff/vectorstuff` preserve type context in composite keys like `FSD_DICT.x.y`.
- Pickles: `res:/localizationfsd/...*.pickle` -> container name minus `.pickle`.
- Traits: Single synthetic container `traits` under miner name `phobos` combining `FsdLite` + `FsdBuilt` data.
- Metadata: Single container `metadata` under miner name `phobos` (client build + timestamp).

## 5. Translation Pattern
When `language` arg is:
- Specific (e.g. `en-us`): Fields are replaced in-place (`Translator.__translation_singlemode`).
- `multi`: Original field retained; new fields appended with suffix `_lang` for each language (`Translator.__translation_multimode`).
Miners must call `translator.translate_container(data, language, verbose=...)` after data normalization (see `SqliteMiner.get_data`, `FsdLiteMiner.get_data`, `FsdBuiltMiner.get_data`). Do NOT translate `FsdBinaryMiner` output yet (currently returns raw introspection results); add only if necessary.

## 6. Adding a New Miner
Implement subclass of `BaseMiner` with:
```
class ExampleMiner(BaseMiner):
    name = 'example'
    def __init__(...): ...
    def contname_iter(self): yield from ...
    def get_data(self, container_name, language=None, verbose=False, **kwargs): ...
```
Return only Python primitives / dict / list / tuple so writers & translator work. Prefer caching heavyweight discovery with `@cachedproperty` (see existing miners). Raise `_container_not_found` for unknown names.
Register it in `run.py` miners list respecting desired order (metadata early, traits after data sources, pickles last, etc.).

## 7. Writing / Grouping Output
`JsonWriter.write` ensures folder per miner (`output/<miner_name>/`). If `--group N` specified, large top-level dicts or lists are chunked deterministically via `_grouping_map`. Keys are natural-sorted before encoding (see `natural_sort`). Preserve this behavior for consistency; if adding new writer types, mirror sorting semantics unless a strong reason not to.

## 8. Integrity & Safety Checks
Always access files through `ResourceBrowser` to enforce size + md5 verification (`__verify_data`). Avoid reading client files directly by path. When modifying FSD loaders logic, clean up `sys.path` and imported modules as `FsdBuiltMiner.get_data` does to prevent memory bloat & stale state.

## 9. Common Pitfalls / Edge Cases
- Translation spec: Some containers might need explicit `spec` list if automatic detection misfires; pass `spec` to `translate_container` when needed.
- Large memory: Bulk FSD structures can be huge; avoid holding multiple full copies. Stream or group if adding new heavy miners.
- Multi-language output greatly enlarges JSON; ensure grouping or selective `--list` usage for performance.
- `FsdBinaryMiner` experimental output may not be JSON-serializable if new object types added; maintain string coercion similar to current helpers.

## 10. Style & Contribution Conventions
- Keep modules self-contained; no third-party deps without adding a manifest.
- Favor functions/methods over global state; use `cachedproperty` for expensive discovery.
- Preserve public method signatures already consumed by `FlowManager` (`contname_iter`, `get_data(language=..., verbose=...)`).
- Maintain Python 3.12 compatibility; if introducing typing or newer features, ensure they exist in 3.12 stdlib.

## 11. Quick Reference
Key files: `run.py`, `flow.py`, `miner/*.py`, `util/translator.py`, `util/eve_normalize.py`, `util/resource_browser.py`, `writer/json_writer.py`.

If unsure about adding a feature, mirror patterns from the closest existing miner/writer.

---
Feedback welcome: Are translation details, FSD binary vs built distinction, or grouping behavior unclear? Specify what to expand or examples needed.
