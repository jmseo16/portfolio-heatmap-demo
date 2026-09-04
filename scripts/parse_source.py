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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_docs import load_doc_scripts  # noqa: E402

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
    "6-1": "the office",
    "6-2": "office then vs. now",
    "6-3": "first job",
    "7-1": "tech at school",
    "7-2": "daily tech",
    "7-3": "home appliances",
    "7-4": "tech then vs. now",
    "7-5": "learning new tech",
    "7-6": "tech for a project",
    "8-1": "favorite park",
    "8-2": "park problems",
    "8-3": "kids vs. adults at the park",
    "10-1": "park invite call",
    "10-2": "park closed, plan B",
    "10-3": "sick day reschedule",
    "10-4": "furniture inquiry call",
    "10-5": "wrong furniture delivered",
    "10-6": "phone unavailable",
    "10-7": "broken new phone",
    "10-8": "MP3 player inquiry",
    "10-9": "broke friend's MP3 player",
    "10-10": "planning a farewell party",
    "10-11": "party venue change",
    "10-12": "missing class after an accident",
    "10-13": "lost finding the academy",
    "10-14": "class too advanced, slow down",
    "10-15": "questions before enrolling",
    "10-16": "class is already full",
    "Industry-1": "famous industry & company",
    "Industry-2": "product that let down the public",
    "Industry-3": "companies young people want",
    "Internet-1": "internet security & addiction",
    "Internet-2": "internet across generations",
    "Weather-1": "weather in your country",
    "Weather-2": "memorable strange weather",
    "Hotel-1": "first hotel stay",
    "Hotel-2": "hotel pool experience",
    "Restaurant-1": "health-conscious menus",
    "Restaurant-2": "favorite restaurant",
    "Food-1": "food contamination incident",
    "9-1": "latest fashion trends",
    "9-2": "favorite website",
    "9-3": "first time online",
    "9-4": "recycling pattern",
    "9-5": "recycling then vs. now",
    "9-6": "recycling tools",
    "9-7": "a recycling difficulty",
    "9-8": "geographic features",
    "11-1": "appointment spots",
    "11-2": "making appointments",
    "11-3": "childhood appointment (dentist)",
    "11-4": "childhood appointment (hair salon)",
}

# Short gists for paragraphs whose own text has no leading "(Cue)" — those
# already double as a beat name (Opening, Reason1, Closing, ...) and don't
# need an override. Keyed by paragraph id, which is stable across re-parses
# as long as row order in the sheet doesn't change.
#
# As of the sheet's "(intro)/(body N)/(closing)" convention, every paragraph
# already carries a clean cue, so this is empty — add an entry here only if
# a future paragraph goes back to having no leading (Cue) at all. Note ids
# are positional (t{topic}-q{question}-p{paragraph}), so an override written
# against one version of the sheet can silently mislabel a later version's
# different paragraph at that same position; if you do add entries, re-check
# them after every re-parse rather than assuming they still apply.
PARAGRAPH_LABEL_OVERRIDES = {}


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
    "Movie": "https://docs.google.com/document/d/1XCXLIe6wjRt_2HMylK4yrDb8MlcjzvA3gd9ams_kgRQ/edit",
    "Concert": "https://docs.google.com/document/d/1hZMUXd-CRytRQ5wgLR6k48_o8_FJoh1BoqCLnIDamkQ/edit",
    "Household": "https://docs.google.com/document/d/1adWRSbndAjmNzGjEjX1sRsIdvKASEDQ-LHINrpAHe3U/edit",
    "Trip": "https://docs.google.com/document/d/1eBtpCU17N7h5XumYlTyG1MdK1V-_O1TfHMgamti1faA/edit",
    "Academy": "https://docs.google.com/document/d/1i-JhV_2QyQAfgxThCMMm73UZ6i_LWUVuT9GHtWoT5EM/edit",
    "Workplace": "https://docs.google.com/document/d/1xWBKQzWvPU-Z9IyI-wNJIXS9rx-Bf89V5VvJFvsRqqE/edit",
    "Technology": "https://docs.google.com/document/d/1sz_HWeE13roBW2Pz8TgoMDxEd_r6tCkTosXTVn7oV74/edit",
    "Park": "https://docs.google.com/document/d/18DMnLAq2GkFTKluC3csJqyRTle9ZMycNQv7-wcXA6_8/edit",
    "Role Play": "https://docs.google.com/document/d/1qBp-jyD1ZZODJ_5GB5bX_s_PRXu6Sy6a5z98zC_C96g/edit",
    "Impromptu": "https://docs.google.com/document/d/1YkFNUYREfa8yvQVmggY80Txa9Tl8bi_9AT6rjsZPme4/edit",
    "Fashion/Internet/Recycling/Geography": "https://docs.google.com/document/d/1_4FP-efQWma3wE5kyrNt_lmwcWqgFJMKuBGMx4_EhxA/edit",
    "Appointment": "https://docs.google.com/document/d/19WZIbQtJx8DQPo3Jipg46zuXwwjIQZiuodxg3wQ19FE/edit",
}


def to_forest(topics, doc_scripts=None):
    doc_scripts = doc_scripts or {}
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
            m = re.match(r"^([A-Za-z0-9]+-\d+)\.\s*(.*)$", q["text"])
            tag = m.group(1) if m else f"Q{qi + 1}"
            qtext = (m.group(2) if m else q["text"]).strip()
            q_label = QUESTION_LABELS.get(tag, tag)
            q_node = {
                "id": f"t{ti}-q{qi}",
                "name": q_label,
                "tag": tag,
                "type": "question",
                "full": qtext,
                "script": doc_scripts.get(tag, ""),
                "children": [],
            }
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
    doc_scripts = load_doc_scripts()
    forest = to_forest(topics, doc_scripts)

    missing_scripts = [
        q["tag"] for t in forest for q in t["children"] if not q.get("script")
    ]
    if missing_scripts:
        print(f"warning: no doc script found for tags: {missing_scripts}", file=sys.stderr)
        print("add the topic's Google Doc under data/docs/ and re-run.", file=sys.stderr)

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
