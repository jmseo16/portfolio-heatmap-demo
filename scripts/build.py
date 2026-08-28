#!/usr/bin/env python3
"""
Inject data/forest.json into templates/mindmap.template.html to produce the
self-contained mindmap.html at the repo root.

Usage:
    python3 scripts/build.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "/*__FOREST_DATA__*/[]/*__END_FOREST_DATA__*/"


def main():
    data = json.loads((ROOT / "data" / "forest.json").read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False)

    template = (ROOT / "templates" / "mindmap.template.html").read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit("placeholder not found in template — did the template change?")

    out_path = ROOT / "mindmap.html"
    out_path.write_text(template.replace(PLACEHOLDER, payload), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
