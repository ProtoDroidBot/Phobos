# Legacy Python 2 Client Support

## Scope

The compatibility layer allows the Python 3.12 Phobos process to extract EVE
clients whose `code.ccp`, native FSD loaders, and auxiliary extensions target
Python 2.7. Build 3396210 is the golden integration target.

The main process never imports Python 2 bytecode or loads a Python 2 native
extension. This prevents ABI conflicts and prevents the extracted client tree
from shadowing Python 3 standard-library modules.

## Runtime detection

`compat.client_profile.detect_client_profile` reads `start.ini`, inspects a
`.pyj` entry from `code.ccp`, and checks for client runtime DLLs. Build 3396210
is detected as `legacy_py27` from Python bytecode magic `03f30d0a` and
`tq/bin64/python27.dll`.

Use `--client-runtime` only to override detection during diagnosis.

## code.ccp

The archive pipeline is:

1. Open `code.ccp` as ZIP.
2. Read a `.pyj` entry.
3. Decompress it with `zlib`.
4. Validate the Python 2.7 `.pyc` magic.
5. Cache the `.pyc` using the entry's package path.

The cache is `.phobos-runtime/<build>`. Its marker records the source archive
path, size, and nanosecond modification time, so an unchanged archive is not
expanded again.

The decompiled ClientCodeGrabber output remains useful for behavioral
reference, but it is not used as an executable import tree. Decompiled modules
may contain artifacts such as top-level `return` statements.

## Data backends

Build 3396210 contains these successful extraction paths:

| Backend | Containers | Runtime |
| --- | ---: | --- |
| Legacy binary `.static` | 31 | Python 3.12 FSD reader |
| SQLite `.static` | 14 | Python 3.12 `sqlite3` |
| Generated `.fsdbinary` loader | 149 | Isolated Python 2.7 worker |
| Standalone SQLite tables | 2 | Python 3.12 `sqlite3` |
| Resource pickle | 15 | Restricted Python 3.12 unpickler |
| Phobos metadata | 1 | Python 3.12 |

## Native worker

`tools/py27host.exe` is a small 64-bit host for the client-supplied
`python27.dll`. It calls the DLL's `Py_Main` in a separate process. The worker
receives and returns JSON files; it never exchanges pickles with Python 3.

Rebuild the host when needed:

```powershell
gofmt -w tools\py27host\main.go
go build -trimpath -ldflags "-s -w" -o tools\py27host.exe tools\py27host\main.go
```

An external 64-bit Python 2.7 executable can instead be selected with
`--python2` or `PHOBOS_PYTHON2`.

The worker loads native modules from their direct `tq/bin64` names after
checking their MD5 against the resource index. This is required on Windows;
loading the hashed `ResFiles` copy does not provide the extension filename
expected by the Python loader.

## planetResources.pickle

The build-3396210 file is a primitive protocol-2 pickle. It contains three
standard-deviation settings and 56 buffers. Each buffer is 3,600 bytes:

* 900 little-endian IEEE-754 `float32` coefficients;
* 30 spherical-harmonic bands (`30 * 30` coefficients);
* a SHA-256 and base64 copy for exact round trips;
* the decoded coefficient array for analysis.

`_eveplanetresources.dll` exports the original spherical-harmonic builder but
also depends on an initialized `blue.dll` runtime. Loading it in a standalone
worker terminates that worker, so Phobos treats it as an unavailable optional
oracle and uses the lossless format decoder. The process boundary prevents such
a native failure from affecting Python 3.12.

### Surface-grid and heatmap decoding

`tools/render_planet_resources.py` performs the next decoding stage without
loading the Python 2 extension:

```text
bufferBase64 -> 900 float32 coefficients -> spherical surface grid -> heatmap
```

Static analysis of `_eveplanetresources.dll`'s `SHBuilder.SHBasisFunc` gives the
basis convention used by the tool:

* coefficient index `l * (l + 1) + m`;
* orthonormal real spherical harmonics with a `sqrt(2)` factor for non-zero `m`;
* associated Legendre polynomials include the Condon-Shortley phase;
* negative `m` uses `sin(abs(m) * phi)` and positive `m` uses `cos(m * phi)`;
* `phi` is longitude and `theta` is colatitude.

The Python implementation evaluates this basis analytically. It intentionally
does not reproduce the native builder's 2,048-step angular lookup-table
quantization, so the grids represent the underlying harmonic more accurately
than the client-era sampling approximation.

Install the optional Python 3.12 dependencies and render all 56 templates:

```powershell
python -m pip install -r requirements-heatmap.txt
python tools\render_planet_resources.py `
  3396210-001\resource_pickle\app__res_planetResources.json
```

The default output folder is
`3396210-001/resource_pickle/planetResources_heatmaps`. It contains labeled PNG
heatmaps, a contact sheet, a JSON manifest, and `surface_grids.npz`. The NPZ
archive stores `longitudeDegrees`, `latitudeDegrees`, and one float32 grid named
`template_XX` per selected template. Heatmaps clamp negative ringing to zero in
the same way as the client code; use `--allow-negative` to visualize raw values.

Use `--templates 0,10-14,55`, `--width`, and `--height` to render a subset or a
different resolution. `--global-scale` makes template colors directly
comparable, while the default per-template scale exposes each template's shape.

## Verification

Install requirements and run the tests:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run selected containers with strict reporting:

```powershell
python run.py -e G:\evejs3396210-2\client\EVE -s tq -j 3396210-001 `
  -l "metadata,achievements,regions,accountingentrytypes,app:/res/planetResources" `
  --strict
```

Run the complete extraction with the canonical command:

```powershell
python run.py -e G:\evejs3396210-2\client\EVE -s tq -j 3396210-001
```

Inspect `_phobos_manifest.json`. A complete build-3396210 extraction contains
212 successful containers and no failed or skipped entries.
