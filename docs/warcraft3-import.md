# Warcraft III files in AIVERSE (Stage 1)

AIVERSE can already load Warcraft III \`.mdx\` / \`.mdl\` models and \`.blp\`
textures natively; see \`engine/render/ModelMdx.cpp\`, \`ModelMdl.cpp\`,
\`ImageBlp.cpp\`, and \`docs/models.md\`. This stage adds a read-only Warcraft
III map importer plus an MPQ unpacker following \`tools/unpackers/PROTOCOL.md\`.

## Quick start

Given a map archive from **your own** Warcraft III installation or a map you
have rights to use:

\`\`\`bash
python3 tools/importers/warcraft3/import.py \
  --source "/path/to/MyMap.w3x" \
  --out "/path/to/AIVERSE-project"
\`\`\`

Reforged also supports a folder named \`MyMap.w3x\` or \`MyMap.w3m\` containing
unpacked map resources. Pass the folder to \`--source\` in the same command.
Folder import uses standard Python 3.8+ and needs no StormLib.

For an actual binary MPQ archive, install the MIT-licensed
[StormLib](https://github.com/ladislav-zezula/StormLib) as a **shared**
library. On macOS, point \`AIVERSE_STORMLIB\` to \`libstorm.dylib\`; on Linux
use \`libstorm.so\`; on Windows use \`StormLib.dll\`. This library is not
vendored or downloaded by AIVERSE.

Output:

\`\`\`text
<project>/content/Warcraft3/MyMap/
    war3map.w3e                 original source, preserved
    war3map.wpm                 original source, preserved
    war3map.wts                 original source, preserved
    Units/.../*.mdx             original model files, if present
    .../*.blp                   original textures, if present
    terrain.json                decoded W3E v11/v12, if present
    pathing.json                decoded WPM, if present
    strings.json                decoded WTS, if present
    imports.json                decoded IMP, if present
    import.json                 manifest and source provenance
\`\`\`

Imported files are exposed through the \`content/\` Assets tree. Existing
native MDX/MDL and BLP decoders can read the corresponding assets without
reimplementation.

### Archive plugin

\`tools/unpackers/mpq/unpacker.json\` registers \`.mpq\`, \`.w3m\`, \`.w3x\`,
\`.w3n\` as external sources. \`assetpipe\` invokes its \`info\` / \`probe\` /
\`list\` / \`extract\` methods. The plugin reads known Warcraft map filenames,
\`(listfile)\`, and \`war3map.imp\` imported filenames. An MPQ with an absent
\`(listfile)\` and unknown hashed filenames cannot be completely enumerated;
extraction of a known filename may still work.

### Interpreting decoded data

- \`terrain.json\`: W3E versions 11 (7-byte tilepoints) and 12 (8-byte
  tilepoints, six-bit ground texture index). Contains tilepoint dimensions,
  center offsets, author-provided ground/cliff tile IDs and raw data alongside
  calculated heights. The \`vertexSchema\` field documents each array element.
  Tilepoints are row-major from the bottom-left in Warcraft coordinates.
- \`pathing.json\`: WPM v0 with lossless base64-encoded cell flags. Restriction
  bit masks are included.
- \`strings.json\`: the WTS \`TRIGSTR_NNN\` string dictionary.
- \`imports.json\`: the IMP import path records with their original flags.

Warcraft uses 128 world units per map cell. The existing native model importer
maps Warcraft's Z-up orientation to AIVERSE's Y-up axes. Decoded terrain retains
Warcraft coordinates and heights; a later TerraWeave adapter must apply the
same transform exactly once.

### Explicit limits

This first stage is **not** a runnable Warcraft III game or a World Editor
clone. It does not yet populate ECS entities, convert terrain to TerraWeave,
spawn doodads or units, resolve object definitions, execute JASS/Lua, render
Warcraft particles/ribbons or read Reforged's installed CASC storage.

The importer refuses overwriting \`content/Warcraft3/<name>\`; import into a
new project or rename the input first. Extraction is atomic and bounded.
Imported third-party assets are marked \`external\`; never commit or distribute
game data unless properly licensed.

### Tests

\`\`\`bash
python3 -m unittest discover -s tests/tools -p test_warcraft3_import.py -v
\`\`\`

Tests use generated W3E v11 and v12, WPM, WTS, IMP, bad-size cases,
archive signature checks, an unpacked folder, and overwrite protection.
A real StormLib/MPQ integration acceptance test is still required.
