# OPIc Forest

An interactive mindmap for OPIc (AL) speaking prep. Every topic from the
script spreadsheet becomes its own tree in a small "forest": topic → question
→ script beat → kick phrase, drawn as a horizontal, click-to-expand map (the
topic in the middle, questions fanning left/right) so you can drill from a
bare topic name down to the exact phrase you rehearsed.

Use the **Fullscreen** button (top-left of the canvas) to hide the top bar
and topic list; press it again (or Esc) to bring them back.

Open **`mindmap.html`** directly in a browser — it's a single self-contained
file (D3 + inlined data, loaded from the CDN allow-list), no build step or
server required.

## How the tree maps to the source

The source is the "(1급) Mind map" Google Sheet (`OPIc Speaking Log` folder),
four columns: `Category, Question, Answer, Kick`. `Category` and `Question`
are only filled on the first row of a group; every row after that is one
more paragraph of that answer.

| Sheet column | Mindmap node | Default state |
|---|---|---|
| Category | topic (center of a tree) | always visible |
| Question | question | always visible |
| Answer | script beat (one row = one paragraph) | hidden until its question is clicked |
| Kick | kick phrase (comma-split into one node each) | hidden until its beat is clicked |

Click a question to reveal its beats; click a beat to reveal its kicks;
click again to collapse. A search box in the top bar matches across every
topic at once (question text, beat text, kick phrases) and jumps + expands
the tree to the result.

Clicking a question shows a **"Kick phrases to use"** list right away —
every beat's kick phrases for that question, grouped by beat, never
hidden — so you can read the question and answer it out loud using just
those phrases as cues, the way you'd actually rehearse for the test.

Below that sits **"Your script"**: an editable text box seeded with that
question's full, polished answer, copied verbatim from the topic's own
Google Doc (the same doc the topic node's "Show script" button links to)
and matched by question tag — not a stitching of the sheet's short
per-beat text. Unlike the kick list, the script itself stays collapsed
behind a "▸ Show script" button by default (so it doesn't spoil the
practice) — click it to reveal the box, or flip the top bar's **"👁 View
all scripts"** toggle to make every question's script open automatically
from then on (that preference is remembered too). Edits autosave to the
browser (`localStorage`), but since that's a per-browser convenience
rather than a durable save, the box also has:

- **Save as .txt** — downloads the current box content as a standalone
  text file (`opic-<tag>-<slug>.txt`).
- **Load file** — reads a `.txt`/`.csv` file back into the box, replacing
  its content (and re-saving to `localStorage`).
- **Reset to original** — discards the local edit and restores the Doc's
  original text.

Handing a downloaded `.txt` back to Claude is the intended way to get an
edited practice script folded back into the *original* Google Doc — Claude
can read the file and apply the edit there directly.

The details panel on the right is resizable — drag the thin vertical
handle on its left edge (desktop only); the width you land on is
remembered for next time. And the top bar has an **Export all scripts** /
**Import all scripts** pair that round-trips every question's script (not
just one) in a single `.txt` file, each question under its own
`===== tag | topic | question =====` heading — export it, edit as many
answers as you like, and either load it back into the page or hand the
whole file to Claude to fold every edit back into its source Doc at once.

Clicking a script beat (a "(intro)"/"(body N)"/"(closing)" node) opens the
same kind of editor for its **kick phrases**: add one, edit one in place,
delete one with its `×`, or reset the beat back to its original set — every
change shows up immediately as kick-phrase nodes under that beat in the
tree itself (not just in the panel). These edits also autosave to
`localStorage` and are included in the bulk export/import above: each
question's block in the exported `.txt` carries a `[kicks]` section
listing every one of its beats' kick phrases (tagged with that beat's own
id, so an edit survives even if you reorder or relabel lines), so importing
a file restores scripts *and* kick phrases together, for every topic at
once, not just whichever one happens to be on screen.

## Updating after you edit the spreadsheet

The page is generated, not hand-edited — re-run the pipeline instead of
touching `mindmap.html` directly.

1. **Export the current sheet.** In Google Sheets: File → Download → `.csv`,
   and save it over `data/opic-source.csv` (same 4 columns, same
   blank-Category/Question convention for follow-up paragraph rows).
2. **Re-parse it into data.** `python3 scripts/parse_source.py`
   — rebuilds `data/forest.json` from the CSV. If the sheet introduces a new
   Korean stage-direction cue (like the existing `(warmly)`, `(coyly)`
   notes), the script will warn about leftover Korean text; add the word to
   the `TRANSLATIONS` dict at the top of `scripts/parse_source.py` and
   re-run — the mindmap is meant to stay all-English.
   A new question or a paragraph with no leading `(Cue)` gets a plain
   fallback label until you add a short hand-picked one to `QUESTION_LABELS`
   / `PARAGRAPH_LABEL_OVERRIDES` in the same file (that's what puts
   "favorite theater" or "the couch" inside a node instead of "1-2" or a
   truncated sentence).
   A new topic also needs its script doc added to `TOPIC_SCRIPT_URLS` in
   `scripts/parse_source.py` — that's the link behind each topic node's
   "Show script" button (its Google Doc, in the same Drive folder as the
   source sheet).
3. **Rebuild the page.** `python3 scripts/build.py`
   — injects `data/forest.json` into `templates/mindmap.template.html` and
   writes the final `mindmap.html`.
4. Commit the changed `data/opic-source.csv`, `data/forest.json`, and
   `mindmap.html`.

## Updating after you edit a topic's script Doc

Each question's editable "Your script" box (see above) is sourced from
`data/docs/<n>-<slug>.txt` — a plain-text export of that topic's Google
Doc — not from the spreadsheet. These are a second, separate source of
truth from `data/opic-source.csv`, so they need their own re-export when
a Doc's *wording* changes (fixing a typo in the sheet doesn't touch these).

1. **Export the Doc.** In Google Docs: File → Download → Plain text
   (`.txt`), and save it over the matching `data/docs/<n>-<slug>.txt`
   (same filename, so `scripts/parse_docs.py` still finds it).
2. **Re-parse and rebuild.** `python3 scripts/parse_source.py && python3
   scripts/build.py` — `parse_source.py` calls into `scripts/parse_docs.py`
   to re-extract each question's script (keyed by its tag, e.g. `"1-1"`)
   from every file in `data/docs/`, folds it into `data/forest.json` as
   that question node's `script` field, then `build.py` re-injects it into
   `mindmap.html`. If a question's tag can't be found in any doc,
   `parse_source.py` prints a warning naming it — that question's script
   box falls back to stitching the sheet's own beat text until fixed.
3. Commit the changed `data/docs/*.txt`, `data/forest.json`, and
   `mindmap.html`.

Doc formatting is inconsistent from one topic to the next (missing periods
after a tag, stray Korean planning notes, an extra numbered list spliced
into the Trip doc, etc.) — `scripts/parse_docs.py` documents each quirk
it works around inline. If a *new* Doc introduces a new quirk, the parser
will either mis-split it or silently swallow a line; spot-check the
printed preview (`python3 scripts/parse_docs.py`) after any re-export.

No Node/npm install needed for this — both scripts are plain Python 3
(standard library only) and `mindmap.html` runs entirely in the browser.

If you'd rather skip the manual export, just ask Claude to update it — it
can re-read the Google Sheet directly and run the same two scripts.

### If the shape of the data changes

Adding a topic, question, beat, or kick phrase needs no code changes — the
tree grows to fit whatever `data/forest.json` contains. Only change the
page logic (`templates/mindmap.template.html`) if you want a fifth level,
a different default-expanded state, or a layout change.

## Files

```
data/opic-source.csv          the sheet, exported as CSV (source of truth)
data/docs/*.txt               each topic's Google Doc, exported as plain text
data/forest.json              parsed topic → question → beat → kick tree
templates/mindmap.template.html  page template with a data placeholder
scripts/parse_docs.py         data/docs/*.txt -> {tag: script text}
scripts/parse_source.py       CSV + parse_docs -> data/forest.json
scripts/build.py              data/forest.json + template -> mindmap.html
mindmap.html                  the built, self-contained page
```
