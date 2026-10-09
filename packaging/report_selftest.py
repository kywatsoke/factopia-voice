"""Turn a self-test result into notices on the workflow run page, and fail
the step when a required check failed.

    python packaging/report_selftest.py <result.json> <label>
"""
import json
import sys
from pathlib import Path


def esc(text):
    return str(text).replace("%", "%25").replace("\r", "").replace("\n", "%0A")


def main():
    path, label = Path(sys.argv[1]), sys.argv[2]
    if not path.exists():
        print(f"::error title={label}::The app did not write a self-test result (it may not have started).")
        return 1
    result = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    for name, check in result["checks"].items():
        mark = "ok" if check["ok"] else ("FAILED" if check["required"] else "failed (optional)")
        detail = check["detail"] if isinstance(check["detail"], str) else json.dumps(check["detail"], ensure_ascii=False)
        lines.append(f"{name}: {mark} ({check['seconds']} s) {detail[:300]}")
        if not check["ok"] and check["required"]:
            print(f"::error title={label}: {name}::{esc(detail[:1500])}")
    print(f"::notice title={label}::{esc(chr(10).join(lines))}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
