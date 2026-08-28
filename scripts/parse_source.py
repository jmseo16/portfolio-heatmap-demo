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

# Short (1-4 word) gists shown inside the question node itself, keyed by the
# sheet's own question tag ("1-1", "2-3", ...) since that's stable across
# re-parses. A question without an entry here falls back to its tag.
QUESTION_LABELS = {
    "1-1": "viewing pattern",
    "1-2": "favorite theater",
    "1-3": "favorite actor",
    "1-4": "memorable movie",
    "1-5": "celebrity gossip",
    "1-6": "movies then vs. now",
    "1-7": "favorite genre",
    "2-1": "recent concert",
    "2-2": "concert mishap",
    "2-3": "listening habits",
    "2-4": "listening devices",
    "2-5": "favorite singers",
    "3-1": "household chores",
    "3-2": "chores growing up",
    "3-3": "chores gone wrong",
    "3-4": "homes then vs. now",
    "3-5": "housing problems",
    "3-6": "favorite furniture",
    "3-7": "newest furniture",
    "3-8": "family memory",
    "4-1": "travel interests",
    "4-2": "why vacation",
    "4-3": "memorable beach",
    "4-4": "staycation",
    "4-5": "travel then vs. now",
    "4-6": "trip planning",
    "5-1": "the academy",
    "5-2": "class curriculum",
    "5-3": "the instructor",
    "5-4": "finding it & directions",
}

# Short gists for paragraphs whose own text has no leading "(Cue)" — those
# already double as a beat name (Opening, Reason1, Closing, ...) and don't
# need an override. Keyed by paragraph id, which is stable across re-parses
# as long as row order in the sheet doesn't change.
PARAGRAPH_LABEL_OVERRIDES = {
    "t0-q3-p2": "agentic AI",
    "t0-q3-p3": "upcoming sequel",
    "t0-q4-p0": "the gossip",
    "t0-q4-p1": "drug scandal",
    "t0-q4-p2": "quitting drugs",
    "t0-q4-p3": "closing",
    "t0-q5-p0": "watching with my sons",
    "t0-q6-p0": "animation genre",
    "t0-q6-p1": "teen action movies",
    "t0-q6-p2": "closing",
    "t1-q0-p1": "Coldplay concert",
    "t1-q0-p2": "the atmosphere",
    "t1-q0-p3": "closing",
    "t1-q1-p0": "opening",
    "t1-q1-p1": "losing my wallet",
    "t1-q1-p2": "canceling the card",
    "t1-q1-p3": "closing",
    "t1-q2-p0": "opening",
    "t1-q2-p3": "closing",
    "t1-q3-p0": "opening",
    "t1-q3-p1": "the CD player era",
    "t1-q3-p2": "the streaming era",
    "t1-q3-p3": "closing",
    "t2-q0-p0": "opening",
    "t2-q1-p0": "opening",
    "t2-q2-p0": "opening",
    "t2-q2-p1": "lesson learned",
    "t2-q2-p2": "closing",
    "t2-q3-p0": "opening",
    "t2-q3-p1": "childhood home",
    "t2-q3-p2": "married life",
    "t2-q3-p3": "closing",
    "t2-q4-p0": "rising prices",
    "t2-q4-p1": "government's solution",
    "t2-q4-p2": "closing",
    "t2-q5-p0": "opening",
    "t2-q5-p1": "the couch",
    "t2-q5-p2": "the family bed",
    "t2-q5-p3": "closing",
    "t2-q6-p0": "opening",
    "t2-q6-p1": "the closet",
    "t2-q6-p2": "the bed",
    "t2-q6-p3": "closing",
    "t2-q7-p0": "opening",
    "t2-q7-p1": "planning the party",
    "t2-q7-p2": "the celebration",
    "t2-q7-p3": "closing",
    "t3-q0-p0": "opening",
    "t3-q0-p1": "local food",
    "t3-q0-p2": "the supermarket",
    "t3-q0-p3": "closing",
    "t3-q1-p0": "opening",
    "t3-q1-p1": "Italy fatigue",
    "t3-q1-p2": "staying in",
    "t3-q1-p3": "closing",
}


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


# Each topic's full, polished script lives in its own Google Doc in the
# same "OPIc Speaking Log" Drive folder as the source sheet (titled
# "1. Movie", "2. Concert/...", etc.) — this is what the topic node's
# "Show script" button links to. Add an entry here whenever a new topic
# gets its own script doc.
TOPIC_SCRIPT_URLS = {
    "Movie": "https://docs.google.com/document/d/1WluGZYRTxFM7hv4Pnlk6EZT109onSSZTaZbMoL9mQlE/edit",
    "Concert": "https://docs.google.com/document/d/1BnG3r7CoET4cR8CaS4vyRPIR8--OiDZmJSprWvz1kOI/edit",
    "Household": "https://docs.google.com/document/d/19B4yCg203uv4W8XwnEmmOePxiSwpeQE45BRqak_7d1I/edit",
    "Trip": "https://docs.google.com/document/d/1V_8saPLmYYukbMmN6q1JK32SYemw-O_dKyIaxaKTJyg/edit",
    "Academy": "https://docs.google.com/document/d/1QY5SjUoTOrKaEmOfgulH1USn8w19cvQhBA8gVuqXWXs/edit",
}


def to_forest(topics):
    forest = []
    for ti, t in enumerate(topics):
        topic_node = {
            "id": f"t{ti}",
            "name": t["name"],
            "type": "topic",
            "full": t["name"],
            "scriptUrl": TOPIC_SCRIPT_URLS.get(t["name"]),
            "children": [],
        }
        for qi, q in enumerate(t["questions"]):
            m = re.match(r"^(\d+-\d+)\.\s*(.*)$", q["text"])
            tag = m.group(1) if m else f"Q{qi + 1}"
            qtext = (m.group(2) if m else q["text"]).strip()
            q_label = QUESTION_LABELS.get(tag, tag)
            q_node = {"id": f"t{ti}-q{qi}", "name": q_label, "tag": tag, "type": "question", "full": qtext, "children": []}
            for pi, p in enumerate(q["paragraphs"]):
                ptext = p["text"].strip()
                if not ptext and not p["kick"].strip():
                    continue
                p_id = f"t{ti}-q{qi}-p{pi}"
                p_label = PARAGRAPH_LABEL_OVERRIDES.get(p_id) or (short_para_label(ptext, pi) if ptext else f"Beat {pi + 1}")
                p_node = {
                    "id": p_id,
                    "name": p_label,
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
