# Phobos
Phobos is script for dumping EVE client data into JSON format.

It uses collection of data miners which extract data from files of various formats. It does not provide stable "API" by design: if CCP changes data scheme within EVE client, output files will also change.

### A note on safety
Several data miners used in Phobos are doing potentially very dangerous thing security-wise, they are loading external code:
 
- ResourcePickleMiner: [unpickles](https://docs.python.org/2.7/library/pickle.html) serialized python files
- FsdBinaryMiner: executes loaders provided by the EVE client to access data in FSD binary format
 
It doesn't mean that you should not use these miners. Generally speaking, if you trust EVE client and Phobos - you should have no issues with these miners. Phobos runs simple validation on files which will be worked upon (checksum according to the client's file registry). Still, it is recommended to run Phobos in some sandboxed environment (e.g. separate Wine prefix for Linux).

### Requirements

* Python 3.12
* 64-bit python built for Windows is needed to access data in FSD binary format
* PyYAML 6.x (`python -m pip install -r requirements.txt`)

### Python 2.7 client compatibility

Phobos continues to run under Python 3.12 when reading clients whose packaged
code and native loaders use Python 2.7. The legacy runtime is isolated from the
main process:

* `code.ccp` is opened as a ZIP archive and its zlib-compressed `.pyj` entries
  are cached as their original Python 2.7 `.pyc` files under
  `.phobos-runtime/<build>`.
* Legacy `.static` files are decoded by a maintained Python 3 reader; client
  bytecode is not imported into Python 3.
* Generated `*Loader.pyd` modules run in a separate process using the matching
  client `python27.dll` through `tools/py27host.exe`.
* Python 2 pickles use a restricted unpickler. Binary values receive an
  explicit lossless JSON representation.

For build 3396210, use:

```powershell
python run.py -e G:\evejs3396210-2\client\EVE -s tq -j 3396210-001
```

Every run writes `_phobos_manifest.json` with client detection, backend,
source MD5, size, and status for every container. Add `--strict` to fail the
command if any requested container cannot be fetched or written.

See [Legacy Python 2 Client Support](docs/LEGACY_PY27.md) for architecture,
testing, worker-host build instructions, and the `planetResources` format.

Decode the extracted `planetResources` coefficients into spherical grids and
heatmaps with `tools/render_planet_resources.py`. The legacy-client guide
documents the real spherical-harmonic convention and output archive.

### Arguments:

* `--eve`: Required. Path to EVE client folder, e.g. `C:\CCP\EVE Online`.
* `--json`: Required. Output folder for JSON files.
* `--server`: Optional. Server to pull data from. Defaults to `stillness`.
* `--translate`: Optional. Specifies language to which strings will be translated. You can choose either individual languages (run script with `--help` argument for a list) or 'multi' option. For individual language, translation will be done in-place (replaces original text with localized text), for multi-language translation, original text is not modified, but new text fields are added, named using `<field name>_<language code>` convention (e.g. `typeName_en-us`). Multi-language translation mode is default.
* `--list`: Optional. Specifies list of comma-separated 'containers' to extract. It uses names the script prints to stdout. For list of all available names you can launch script without specifying this option, as by default it extracts everything it can find.

### Example

    $ python run.py --eve=E:\eve\client\ --json=~\Desktop\phobos_tq_en-us --list="evetypes, marketgroups, metadata"

## EVE Universe Database Generator

The `generate.py` script extracts EVE universe data from Phobos output and creates a normalized SQLite database with systems, constellations, regions, and jump connections. This is particularly useful for creating navigation tools, route planners, and universe analysis applications for EVE Frontier.

### Requirements for generate.py

* Phobos output files (run the main extraction first)
* Python 3.7+ (no additional dependencies required)

### Usage

First, run Phobos to extract the raw EVE client data:

    $ python run.py --eve="C:\CCP\EVE Frontier" --json=output --translate=multi

Then use the generated output to create the universe database:

    $ python generate.py --output eve_universe.db --phobos-output ./output

### Arguments for generate.py

* `--output` or `-o`: Optional. Output SQLite database path (default: `eve_universe.db`)
* `--phobos-output` or `-p`: Optional. Path to Phobos output directory (default: `./output`)
* `--query` or `-q`: Optional. Run a simple query on the database after creation

### Examples

Create a database with default settings:

    $ python generate.py

Create a database with custom paths:

    $ python generate.py --output frontier_universe.db --phobos-output ./phobos_data

Create database and run a query:

    $ python generate.py --query "SELECT COUNT(*) FROM SolarSystems"

Coordinate values are stored in the generated database as exact decimal
`TEXT`, preserving the complete IEEE-754 double representation emitted by the
FSD loader. Cast a coordinate explicitly for numeric calculations, for example
`CAST(centerX AS REAL)`.

### Database Schema

The generated SQLite database contains the following tables:

* **Regions**: Region data with coordinates
* **Constellations**: Constellation data with region links  
* **SolarSystems**: Solar systems with coordinates, star data, constellation/region links
* **Jumps**: Stargate connections between systems (bidirectional)
* **Planets**: Planet data with celestial information and proper naming
* **Moons**: Moon data orbiting planets with proper naming
* **NpcStations**: NPC-owned stations in space

## Other Tools

### Image Extractor
`generate_image_zip.py` extracts item icons from the EVE client resource files and packages them into a ZIP archive.
See [SCRIPTS_REFERENCE.md](docs/SCRIPTS_REFERENCE.md#generate_image_zippy) for usage.

### Output Cleaner
`tools/tidy_outputs.py` reduces the size of Phobos JSON output by removing redundant or constant keys.
See [SCRIPTS_REFERENCE.md](docs/SCRIPTS_REFERENCE.md#toolstidy_outputspy) for usage.

### Sample Queries

Show systems with their jump connections:
```sql
SELECT s.name, COUNT(j.toSystemId) as connections 
FROM SolarSystems s 
LEFT JOIN Jumps j ON s.solarSystemId = j.fromSystemId 
GROUP BY s.solarSystemId 
ORDER BY connections DESC 
LIMIT 10;
```

Find route between systems (basic):
```sql
WITH RECURSIVE route(system_id, path, hops) AS (
  SELECT 30000001, '30000001', 0
  UNION
  SELECT j.toSystemId, path || '->' || j.toSystemId, hops + 1
  FROM route r, Jumps j 
  WHERE r.system_id = j.fromSystemId AND hops < 5 AND j.toSystemId = 30000002
)
SELECT * FROM route WHERE system_id = 30000002;
```

Show planets in a system with proper naming:
```sql
SELECT name, celestialIndex, radius, orbitRadius 
FROM Planets 
WHERE solarSystemId = 30005266
ORDER BY celestialIndex;
```

Find all moons of a specific planet:
```sql
SELECT m.name, m.celestialIndex, m.radius, m.orbitRadius
FROM Moons m
JOIN Planets p ON m.planetId = p.planetId
WHERE p.name = 'U87-QF1 - Planet 4'
ORDER BY m.celestialIndex;
```

### Performance

The script processes approximately:
- 24,400+ systems from EVE Frontier universe data
- 7,400+ stargate connections
- 83,300+ planets with proper naming
- 152,500+ moons with hierarchical naming 
- 50+ NPC stations 
- Complete extraction typically takes 10-30 seconds

### Phobos-specific data
Besides raw data Phobos pulls from client, it provides two custom containers.

#### phobos/metadata
Contains just two parameters: client version and UNIX timestamp of the time script was invoked.

#### phobos/traits
Traits for various ships. Data has following format:

    Returned value:
      For single language: ({'typeID': int, 'traits': traits}, ...)
      For multi-language: ({'typeID': int, 'traits_en-us': traits, 'traits_ru': traits, ...}, ...)
      Traits: {'skills': (skill section, ...), 'role': role section, 'misc': misc section}
        // skills, role and misc fields are optional
      Section: {'header': string, 'bonuses': (bonus, ...)}
      Bonus: {'number': string, 'text': string}
        // number field is optional

For example, Cambion traits in JSON format:

    {
      "traits": {
        "role": {
          "bonuses": [
            {"number": "115%", "text": "bonus to kinetic Light Missile and Rocket damage"},
            {"number": "50%", "text": "reduction in module heat damage amount taken"},
            {"text": "·Can fit Assault Damage Controls"}
          ],
          "header": "Role Bonus:"
        }, 
        "skills": [
          {
            "bonuses": [{"number": "5%", "text": "bonus to Light Missile and Rocket Launcher rate of fire"}],
            "header": "Assault Frigates bonuses (per skill level):"
          },
          {
            "bonuses": [{"number": "4%", "text": "bonus to all shield resistances"}],
            "header": "Caldari Frigate bonuses (per skill level):"
          }
        ]
      },
      "typeID": 32788
    },
