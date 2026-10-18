"""Inspect vendor fixed-runtime mixed-architecture helpers on Windows."""

import json
from pathlib import Path
import struct
import subprocess
import tempfile
import pefile
from prepare_model import download, verify_microsoft, digest
from prepare_windows_runtime import SOURCE, CAB_HASH


def main():
    archive = download(SOURCE, Path('.local/downloads/webview-inspection.cab'), CAB_HASH)
    with tempfile.TemporaryDirectory(prefix='stanicode-webview-inspect-') as directory:
        root = Path(directory)
        subprocess.run(['expand.exe', str(archive.resolve()), '-F:*', str(root)], check=True, stdout=subprocess.DEVNULL)
        executables = list(root.rglob('msedgewebview2.exe'))
        if len(executables) != 1:
            raise ValueError('Ambiguous fixed runtime')
        runtime = executables[0].parent
        verify_microsoft(executables[0])
        for path in runtime.rglob('*'):
            if path.suffix.lower() not in {'.exe', '.dll'}:
                continue
            with pefile.PE(str(path), fast_load=False) as binary:
                if binary.FILE_HEADER.Machine == 0x8664:
                    continue
                clr = binary.OPTIONAL_HEADER.DATA_DIRECTORY[14]
                flags = struct.unpack_from('<I', binary.get_data(clr.VirtualAddress, 20), 16)[0] if clr.VirtualAddress else None
                record = {'file': path.relative_to(runtime).as_posix(), 'machine': hex(binary.FILE_HEADER.Machine),
                          'clr_flags': flags, 'sha256': digest(path),
                          'imports': [entry.dll.decode('ascii') for entry in getattr(binary, 'DIRECTORY_ENTRY_IMPORT', [])]}
                print('::notice title=Official fixed runtime auxiliary PE::' + json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
