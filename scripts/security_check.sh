#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[security-check] ERROR: $*" >&2
  exit 1
}

info() {
  echo "[security-check] $*"
}

info "Checking for disallowed tracked paths"
tracked_forbidden=$(git ls-files apk captures 2>/dev/null || true)
if [[ -n "$tracked_forbidden" ]]; then
  echo "$tracked_forbidden" >&2
  fail "Tracked local-only research/capture files detected"
fi

info "Running metadata validation"
python3 - <<'PY'
import json
import tomllib
from pathlib import Path

json.loads(Path('custom_components/astralpool_halo_cloud/manifest.json').read_text())
json.loads(Path('hacs.json').read_text())
tomllib.loads(Path('pyproject.toml').read_text())
print('metadata_ok')
PY

info "Running Python compile checks"
python3 -m compileall custom_components/astralpool_halo_cloud pychlorinator_cloud >/dev/null

info "Scanning tracked files for obvious secrets or local-only values"
python3 - <<'PY'
import subprocess
import sys
from pathlib import Path

patterns = {
    'jwt_like_token': r'eyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.',
    'hardcoded_ha_token': r'HA_TOKEN\s*=\s*"',
    'hardcoded_halo_password': r'HALO_PASSWORD\s*=\s*"',
    'hardcoded_password_flag_default': r'--password", default=',
    'private_lan_10_10': r'10\.10\.',
    'known_old_serial': r'\b2642931\b',
}

tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True).stdout.splitlines()
text_files = [
    p for p in tracked
    if not p.startswith('apk/')
    and not p.startswith('captures/')
    and p != 'scripts/security_check.sh'
]
problem = False
for label, pattern in patterns.items():
    cmd = ['rg', '-nH', '-I', '-e', pattern, *text_files]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        print(f'[{label}]')
        print(res.stdout.strip())
        problem = True
if problem:
    sys.exit(1)
print('secret_scan_ok')
PY

info "Security check passed"
