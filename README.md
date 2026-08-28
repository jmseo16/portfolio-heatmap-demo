# OPIc Forest

An interactive mindmap for OPIc (AL) speaking prep. Every topic from the
script spreadsheet becomes its own tree in a small "forest": topic → question
→ script beat → kick phrase, drawn as a radial, click-to-expand map so you
can drill from a bare topic name down to the exact phrase you rehearsed.

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
3. **Rebuild the page.** `python3 scripts/build.py`
   — injects `data/forest.json` into `templates/mindmap.template.html` and
   writes the final `mindmap.html`.
4. Commit the changed `data/opic-source.csv`, `data/forest.json`, and
   `mindmap.html`.

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
data/forest.json              parsed topic → question → beat → kick tree
templates/mindmap.template.html  page template with a data placeholder
scripts/parse_source.py       CSV -> data/forest.json
scripts/build.py              data/forest.json + template -> mindmap.html
mindmap.html                  the built, self-contained page
```
