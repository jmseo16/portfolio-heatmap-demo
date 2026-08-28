#!/usr/bin/env python3
"""
Turn the OPIc script spreadsheet (exported as CSV) into data/forest.json,
the hierarchy the mindmap page reads.

Expected CSV columns (matches the "(1급) Mind map" Google Sheet):
  Category | Question | Answer | Kick
Category and Question are only filled on the FIRST row of each group;
every following row (blank Category/Question) is one more paragraph
("script beat") of that answer, with its own Kick phrases.

Usage:
    python3 scripts/parse_source.py [source.csv] [out.json]

Defaults to data/opic-source.csv -> data/forest.json.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Korean delivery/tone cues that have shown up in the sheet, mapped to their
# English equivalent. Add to this dict if new Korean notes appear later.
# Multi-word phrases must come before the individual words they contain,
# since replacement runs in insertion order.
TRANSLATIONS = {
    "슬프게→희망차게": "sadly → hopefully",
    "반갑게": "warmly",
    "눼눼": "nonchalantly",
    "급박하게": "urgently",
    "능청스럽게": "coyly",
    "들떠서": "excitedly",
    "뭉개기": "stalling",
    "속삭이며": "whispering",
    "슬프게": "sadly",
    "희망차게": "hopefully",
}

KOREAN = re.compile(r"[가-힣]+")


def translate(text: str) -> str:
    if not text:
        return text
    out = text
    for kor, eng in TRANSLATIONS.items():
        out = out.replace(kor, eng)
    return out


def short_para_label(text: str, idx: int) -> str:
    m = re.match(r"^\(([^)]{1,28})\)\s*", text)
    if m:
        return m.group(1).strip()
    words = text.split()
    label = " ".join(words[:4])
    if len(label) > 24:
        label = label[:22].rstrip() + "…"
    return label or f"Beat {idx + 1}"


def parse_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    rows = rows[1:]  # drop header

    topics, topic_map = [], {}
    cur_topic = cur_question = None

    for r in rows:
        while len(r) < 4:
            r.append("")
        cat, q, ans, kick = (translate(c.strip()) for c in r[:4])

        if cat:
            cur_topic = cat
            if cat not in topic_map:
                topic_map[cat] = {"name": cat, "questions": []}
                topics.append(topic_map[cat])
        if q:
            q = re.sub(r"^(\d+-\d+\.)\s*[★┅]\s*\d+\.\s*", r"\1 ", q)
            cur_question = {"text": q, "paragraphs": []}
            topic_map[cur_topic]["questions"].append(cur_question)
        if ans or kick:
            cur_question["paragraphs"].append({"text": ans, "kick": kick})

    return topics


def to_forest(topics):
    forest = []
    for ti, t in enumerate(topics):
        topic_node = {"id": f"t{ti}", "name": t["name"], "type": "topic", "full": t["name"], "children": []}
        for qi, q in enumerate(t["questions"]):
            m = re.match(r"^(\d+-\d+)\.\s*(.*)$", q["text"])
            tag = m.group(1) if m else f"Q{qi + 1}"
            qtext = (m.group(2) if m else q["text"]).strip()
            q_node = {"id": f"t{ti}-q{qi}", "name": tag, "type": "question", "full": qtext, "children": []}
            for pi, p in enumerate(q["paragraphs"]):
                ptext = p["text"].strip()
                if not ptext and not p["kick"].strip():
                    continue
                p_node = {
                    "id": f"t{ti}-q{qi}-p{pi}",
                    "name": short_para_label(ptext, pi) if ptext else f"Beat {pi + 1}",
                    "type": "paragraph",
                    "full": ptext,
                    "children": [
                        {"id": f"t{ti}-q{qi}-p{pi}-k{ki}", "name": k, "type": "kick", "full": k}
                        for ki, k in enumerate(x.strip() for x in p["kick"].split(","))
                        if k.strip()
                    ],
                }
                q_node["children"].append(p_node)
            topic_node["children"].append(q_node)
        forest.append(topic_node)
    return forest


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "opic-source.csv"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "forest.json"

    topics = parse_csv(src)
    forest = to_forest(topics)

    remaining = {ch for t in forest for ch in json.dumps(t, ensure_ascii=False) if KOREAN.match(ch)}
    if remaining:
        print(f"warning: untranslated Korean characters remain: {sorted(remaining)}", file=sys.stderr)
        print("add them to TRANSLATIONS in this script and re-run.", file=sys.stderr)

    out.write_text(json.dumps(forest, ensure_ascii=False), encoding="utf-8")
    q_count = sum(len(t["children"]) for t in forest)
    p_count = sum(len(q["children"]) for t in forest for q in t["children"])
    print(f"wrote {out} — {len(forest)} topics, {q_count} questions, {p_count} script beats")


if __name__ == "__main__":
    main()
