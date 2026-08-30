#!/usr/bin/env python3
"""
Inject data/forest.json into templates/mindmap.template.html to produce the
self-contained mindmap.html at the repo root, and write a tiny index.html
redirect alongside it so GitHub Pages' root URL lands on the mindmap
without needing a duplicate copy of the (large, generated) file.

Usage:
    python3 scripts/build.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "/*__FOREST_DATA__*/[]/*__END_FOREST_DATA__*/"

# GitHub Pages serves whatever's at the repo root; mindmap.html isn't named
# index.html (it doubles as the file this repo's README and the Claude
# Artifact both point at directly), so this redirect is what makes the bare
# Pages URL (https://<user>.github.io/<repo>/) land on it too. Static and
# data-independent, but generated here (rather than hand-committed) so it
# stays part of the same build step and can't drift out of sync.
INDEX_REDIRECT = """<!doctype html>
<meta charset="utf-8">
<title>OPIc Forest</title>
<meta http-equiv="refresh" content="0; url=mindmap.html">
<link rel="canonical" href="mindmap.html">
<p>Redirecting to <a href="mindmap.html">the mindmap</a>…</p>
"""


def main():
    data = json.loads((ROOT / "data" / "forest.json").read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False)

    template = (ROOT / "templates" / "mindmap.template.html").read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit("placeholder not found in template — did the template change?")

    out_path = ROOT / "mindmap.html"
    out_path.write_text(template.replace(PLACEHOLDER, payload), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")

    index_path = ROOT / "index.html"
    index_path.write_text(INDEX_REDIRECT, encoding="utf-8")
    print(f"wrote {index_path}")


if __name__ == "__main__":
    main()
