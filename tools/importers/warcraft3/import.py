#!/usr/bin/env python3
"""Import a Warcraft III map archive or unpacked .w3x/.w3m folder into AIVERSE Assets.

python3 tools/importers/warcraft3/import.py --source MAP.w3x --out MY_AIVERSE_PROJECT

Creates content/Warcraft3/<map>/ with original resources (native MDX/MDL/BLP
loaders already exist) and decoded terrain/pathing/strings/manifest JSON.
This is read-only source import, NOT a playable map converter or a TerraWeave scene.
MPQ input requires StormLib; folder maps require only Python 3.8+.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'unpackers' / 'mpq'))
import formats as wc3  # noqa: E402
from unpack import Archive, MAX_FILE, MAX_ENTRIES, probe, valid_name  # noqa: E402


class FolderSource:
    def __init__(self, source):
        self.source = source

    def items(self):
        files = sorted((p for p in self.source.rglob('*') if p.is_file() and not p.is_symlink()),
                       key=lambda p: str(p).lower())
        if len(files) > MAX_ENTRIES:
            raise ValueError('too many files in map folder')
        for file in files:
            if any(part.is_symlink() for part in file.parents if part != self.source.parent):
                raise ValueError('symlink in map folder: ' + str(file))
            rel = file.relative_to(self.source).as_posix()
            if not valid_name(rel):
                raise ValueError('invalid map source path: ' + rel)
            if file.stat().st_size > MAX_FILE:
                raise ValueError('oversized map file: ' + rel)
            yield rel, file.read_bytes()


def source_items(path):
    if path.is_dir():
        yield from FolderSource(path).items()
    elif path.is_file() and probe(str(path)):
        with Archive(str(path)) as archive:
            for name in archive.names():
                yield name, archive.read(name)
    else:
        raise ValueError('expected MPQ .w3x/.w3m archive or unpacked map folder: ' + str(path))


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n',
                    encoding='utf-8')


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True, help='existing AIVERSE project root')
    args = ap.parse_args(argv)
    try:
        source = args.source.expanduser().resolve()
        root = args.out.expanduser().resolve()
        slug = re.sub('[^a-zA-Z0-9_-]+', '_', source.stem).strip('_') or 'map'
        target = root / 'content' / 'Warcraft3' / slug
        if source.is_dir() and source.suffix.lower() not in ('.w3x', '.w3m'):
            raise ValueError('unpacked map folder must end in .w3x or .w3m')
        if target.exists():
            raise ValueError('target already exists (will not overwrite): ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.wc3-', dir=str(target.parent)) as tmp:
            stage = Path(tmp)
            seen = set()
            decoded_files = {}
            total = 0
            result = {'format': 'aiverse.warcraft3.import.v1', 'sourceName': source.name,
                      'external': True, 'files': [], 'decoded': {},
                      'limitations': ['Imported resources are not automatically placed in an ECS scene',
                                      'Terrain JSON is source data, not a TerraWeave world']}
            for rel, data in source_items(source):
                norm = rel.replace('\\', '/')
                if not valid_name(norm):
                    raise ValueError('unsafe source entry: ' + rel)
                key = norm.casefold()
                if key in seen:
                    raise ValueError('case-insensitive filename collision: ' + norm)
                seen.add(key)
                total += len(data)
                if len(seen) > MAX_ENTRIES or total > 4 * 1024**3:
                    raise ValueError('map extraction exceeds safety limit')
                dst = stage / norm
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                result['files'].append({'path': norm, 'size': len(data)})
                basename = norm.lower().replace('\\', '/')
                parser = {
                    'war3map.w3e': ('terrain.json', wc3.terrain),
                    'war3map.wpm': ('pathing.json', wc3.pathing),
                    'war3map.wts': ('strings.json', wc3.strings),
                    'war3map.imp': ('imports.json', wc3.imported),
                }.get(basename)
                if parser:
                    out_name, parse = parser
                    decoded = parse(data)
                    decoded_files[out_name] = decoded
                    result['decoded'][basename] = out_name
            if not result['files']:
                raise ValueError('no files found in source')
            for out_name, doc in decoded_files.items():
                if (stage / out_name).exists():
                    raise ValueError('decoded output collides with original file: ' + out_name)
                write_json(stage / out_name, doc)
            if (stage / 'import.json').exists():
                raise ValueError('import manifest collides with original file')
            result['files'].sort(key=lambda e: e['path'].casefold())
            result['fileCount'] = len(result['files'])
            result['totalBytes'] = total
            write_json(stage / 'import.json', result)
            os.replace(str(stage), str(target))
        print(json.dumps({'ok': True, 'target': str(target), 'files': result['fileCount'],
                          'decoded': result['decoded']}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as ex:
        print(json.dumps({'ok': False, 'error': str(ex)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(run())
