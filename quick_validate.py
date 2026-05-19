from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from k_resdev_skill.schema_tools import validate_json_file


VALIDATION_PAIRS = [
    ("profile-pack-package-receipt-record", "templates/profile-pack-package-receipt-record.json"),
    ("profile-pack-package-receipt-summary", "templates/profile-pack-package-receipt-summary.json"),
    ("admin-profile-pack", "templates/admin-obligation-profile-pack.json"),
    ("admin-profile-pack-review", "templates/admin-obligation-profile-pack-review.json"),
    ("admin-obligations", "templates/admin-obligations.json"),
    ("settlement-binder", "templates/settlement-binder.json"),
    ("admin-change-ledger", "templates/admin-change-ledger.json"),
    ("admin-calendar", "templates/admin-calendar.json"),
]


def main() -> int:
    root = ROOT
    ok = True
    ok = compileall.compile_dir(root / "src", quiet=1) and ok
    for schema, template in VALIDATION_PAIRS:
        result = validate_json_file(root / template, schema)
        if not result["valid"]:
            ok = False
            print(f"{template} failed {schema}: {result['errors']}")
    version = subprocess.run([sys.executable, "-m", "k_resdev_skill", "--version"], cwd=root, text=True, capture_output=True)
    if version.returncode != 0:
        ok = False
        print(version.stderr or version.stdout)
    else:
        print(version.stdout.strip())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
