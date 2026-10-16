"""Read-only comparison of a local official fix diff against candidate source.

A failed comparison is inconclusive: another backport or absent prerequisite
may change the context. A matching diff does not establish full CVE coverage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def compare(source, patch):
    results = {}
    for direction in ('reverse', 'forward'):
        # --force on reverse prevents GNU patch from silently ignoring -R.
        command = ['patch', '--dry-run', '--fuzz=0', '-p1',
                   *(['--reverse', '--force'] if direction == 'reverse' else ['--forward', '--batch']),
                   '-i', str(patch.resolve())]
        process = subprocess.run(command, cwd=source, text=True, errors='replace',
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        results[direction] = {'exit_code': process.returncode, 'diagnostics': process.stdout}
    reverse = results['reverse']['exit_code'] == 0
    forward = results['forward']['exit_code'] == 0
    status = ('reverse_patch_matches' if reverse and not forward else
              'forward_patch_matches' if forward and not reverse else 'manual_review')
    return {'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(), 'status': status,
            'source_modified': False, 'coverage_established': False, 'directions': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--patch', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = compare(args.source, args.patch)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], '(source unchanged; not a coverage certificate)')


if __name__ == '__main__':
    main()
