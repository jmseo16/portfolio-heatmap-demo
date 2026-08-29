#!/usr/bin/env python3
"""
Parse the per-topic Google Docs (the "work files" with the polished, full
prose scripts) into a tag -> script-text mapping, e.g. "1-1" -> "Ok, I'm
gonna tell you about my patterns...".

These are the SAME docs linked from each topic node's "Show script" button
(see TOPIC_SCRIPT_URLS in parse_source.py). The raw doc text is checked in
under data/docs/<n>-<slug>.txt as the source of truth; re-export a doc
whenever its Google Doc changes (Drive -> download as plain text) and
re-run this alongside parse_source.py.

Doc format quirks handled here:
  - Question headers are usually "N-M. <question text>" but the period
    after the tag is sometimes missing ("7-2 <...>"), and the tag can be
    followed by other stray characters before the "<" (household's
    "3-4. <★14. I would like...", park's "8-3 <14. Compare...").
  - Header lines often carry a trailing Korean note after the closing
    ">" (color/word-count hints, "신경 안써도 됨" asides, etc.) - these are
    discarded along with the header line itself, since the question text
    already lives in forest.json via the CSV.
  - Some docs interleave extra "N.   <text>" numbered-list blocks that are
    NOT question headers (e.g. the Trip doc has an interviewer's own
    survey-option list, "1.   You indicated...", spliced between 4-2 and
    4-3) - these are stripped out of the answer body by
    _drop_stray_lists().
  - The Workplace doc doesn't use "N-M." tags at all: each question is
    introduced by a Korean planning-note line starting "1 ", "2 ", "3 "
    (topic-relative position), followed by the actual "<question>" line on
    the next line. Handled by _parse_workplace() with a fixed positional
    tag mapping.

Usage (as a library):
    from parse_docs import load_doc_scripts
    scripts = load_doc_scripts(ROOT / "data" / "docs")   # {"1-1": "...", ...}
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "docs"

# filename -> ordered list of tags, in the order questions appear in that
# doc. Every doc except Workplace carries its own "N-M." tags inline, so
# this is only actually consulted for Workplace's positional headers.
WORKPLACE_TAGS = ["6-1", "6-2", "6-3"]

HEADER_RE = re.compile(r"^(\d+-\d+)\.?\s*<", re.MULTILINE)
STRAY_LIST_LINE_RE = re.compile(r"^\d+\.\s{2,}\S")
ARROW_NOTE_RE = re.compile(r"^→")
KOREAN_RE = re.compile(r"[가-힣]")


def _drop_stray_lists(paragraphs):
    """Remove paragraphs that aren't actually part of the answer script:
    the interviewer's own inserted numbered-option lists / arrow notes,
    a second alternate-phrasing "<question>" line stacked right after the
    header (the Trip doc's 4-5 does this), or a leftover Korean planning
    note (e.g. the Household doc's 3-6 has one before the real answer)."""
    kept = []
    for p in paragraphs:
        lines = p.splitlines()
        if all(STRAY_LIST_LINE_RE.match(l) or ARROW_NOTE_RE.match(l) or not l.strip() for l in lines):
            continue
        if p.startswith("<") and p.endswith(">"):
            continue
        if KOREAN_RE.search(p):
            continue
        kept.append(p)
    return kept


def _clean_body(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # normalize the curly apostrophes/quotes the docs use into the plain
    # ASCII kind so the mindmap renders consistently.
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text)]
    paragraphs = [p for p in paragraphs if p]
    paragraphs = _drop_stray_lists(paragraphs)
    # collapse any leftover single-newline wrapping within a paragraph
    paragraphs = [re.sub(r"\s*\n\s*", " ", p).strip() for p in paragraphs]
    return "\n\n".join(paragraphs)


def _parse_tagged(text: str) -> dict:
    """Docs that carry their own inline 'N-M.' tags."""
    out = {}
    matches = list(HEADER_RE.finditer(text))
    for i, m in enumerate(matches):
        tag = m.group(1)
        # body starts after this header's own line...
        header_line_end = text.index("\n", m.end())
        start = header_line_end + 1
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[tag] = _clean_body(text[start:end])
    return out


def _parse_workplace(text: str) -> dict:
    """The Workplace doc: Korean planning-note lines '1 ...' / '2 ...' /
    '3 ...' introduce each question, with the actual '<question>' line
    right after, then the answer body until the next marker."""
    marker_re = re.compile(r"^[123]\s+\S", re.MULTILINE)
    markers = list(marker_re.finditer(text))
    out = {}
    for i, m in enumerate(markers):
        block_end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        block = text[m.start():block_end]
        # skip the Korean planning-note line and the '<question>' line;
        # the body is everything after the line containing the closing '>'
        lines = block.split("\n")
        body_start_idx = None
        for idx, line in enumerate(lines):
            if ">" in line:
                body_start_idx = idx + 1
                break
        body = "\n".join(lines[body_start_idx:]) if body_start_idx is not None else ""
        if i < len(WORKPLACE_TAGS):
            out[WORKPLACE_TAGS[i]] = _clean_body(body)
    return out


def load_doc_scripts(docs_dir: Path = DOCS_DIR) -> dict:
    """Returns {tag: script_text} merged across every doc in docs_dir."""
    scripts = {}
    for path in sorted(docs_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        if path.name == "6-workplace.txt":
            parsed = _parse_workplace(text)
        else:
            parsed = _parse_tagged(text)
        overlap = set(parsed) & set(scripts)
        if overlap:
            print(f"warning: {path.name} re-defines tags already seen: {sorted(overlap)}")
        scripts.update(parsed)
    return scripts


def main():
    scripts = load_doc_scripts()
    print(f"parsed {len(scripts)} question scripts from {DOCS_DIR}:")
    for tag in sorted(scripts, key=lambda t: tuple(map(int, t.split("-")))):
        preview = scripts[tag][:60].replace("\n", " ")
        print(f"  {tag}: {len(scripts[tag])} chars — {preview}...")


if __name__ == "__main__":
    main()
