---
name: script-update
description: |
  Pull newly-added OPIc questions/scripts from the "OPIc Speaking Log" Google
  Drive folder into this repo's mindmap (data/opic-source.csv, data/docs/,
  data/forest.json, mindmap.html/index.html) and deploy. Use this whenever
  the user says "스크립트 업데이트", asks to sync/update the mind map from
  Drive, says new questions or scripts were uploaded to a topic doc, or asks
  to pull the latest OPIc content from Google Drive into the site. Always
  additive — never modifies or deletes existing rows/scripts/takes/recordings.
---

# Script Update (스크립트 업데이트)

Pulls newly-added OPIc topics/questions from the user's Google Drive "OPIc
Speaking Log" folder into this repo's data pipeline, regenerates the mind
map, and deploys it. This is a purely additive sync: existing rows, scripts,
kick phrases, takes, ratings, and recordings must never be changed or lost —
if you can't guarantee that for a step, stop and ask rather than guess.

## Drive layout (as of the last run — re-verify IDs with search_files, don't
trust these blindly if the folder structure looks different)

- **OPIc Speaking Log** folder (`157kdeoKv1T_LllLEF_ndZ1ULIR3jRnjG`): holds
  one Google Doc per topic (titled like `"1. Movie"`, `"10. Role Play"`,
  `"0. 돌발"`), the live `"(1급) Mind map"` Google Sheet, and a `backup/`
  subfolder (`10zKWpFxLk7nVGaSt02_kD9lmuyQ4PtjS`) holding every prior backup
  of that sheet.
- The **"(1급) Mind map"** sheet is the canonical source the user edits by
  hand; it mirrors `data/opic-source.csv` in this repo (columns `Catergory,
  Question, Answer, Kick` — note the sheet's header really does say
  "Catergory", don't "fix" the typo).
- Each topic Doc is the full, polished verbatim script for that topic's
  questions; it mirrors one file under `data/docs/<n>-<slug>.txt` in this
  repo and is what the mindmap's "Show script" button links to.

## Procedure

### 1. Find what's new

List the Speaking Log folder's Docs with `search_files`
(`parentId = '157kdeoKv1T_LllLEF_ndZ1ULIR3jRnjG' and mimeType =
'application/vnd.google-apps.document'`, `excludeContentSnippets: true` —
content snippets on a full folder listing can blow past the tool's output
limit). Compare each Doc's `modifiedTime` against today's date and against
what's already reflected in `data/opic-source.csv` / `data/forest.json` —
don't assume only the topic(s) the user named changed; the user's own
instructions for this workflow were explicit that *every* topic doc should
be checked, not just the one(s) they happened to mention. A doc with an
old `modifiedTime` needs no further action.

For each doc that changed, `download_file_content` with `exportMimeType:
"text/plain"` (content comes back base64 — decode it) and diff its
questions against what's already in `data/opic-source.csv` (match by tag,
e.g. `10-4`, `0-a1`) to find which questions are genuinely new versus
already imported.

### 2. Handle an unfamiliar tag scheme

Most docs tag questions `N-M.` (e.g. `7-2`, `10-3`). If a new topic uses a
different scheme (e.g. "0. 돌발" uses `0-a1`/`0-a2`/`0-a3`/`0-b1`/`0-b2` —
lettered sub-groups), widen the tag regexes rather than special-casing the
topic:
- `scripts/parse_docs.py`'s `HEADER_RE` (currently
  `r"^(\d+-[a-z]?\d+)\.?\s*<"`)
- `scripts/parse_source.py`'s tag-extraction regex in `to_forest()`
  (currently `r"^(\d+-[a-z]?\d+)\.\s*(.*)$"`)

Both already accept an optional single lowercase letter before the trailing
digits, which covers `0-a1` style tags. If a future doc uses a scheme these
don't cover, widen them further (or, only as a last resort — e.g. the doc
doesn't carry inline tags at all — add a dedicated parser function
following the precedent of `_parse_workplace()` in `parse_docs.py`).

### 3. Compose the CSV rows

For each new question, append rows to the END of `data/opic-source.csv`
(never insert into the middle of existing content, even if that changes
the display order the user expects — the position of the topic among
existing topics doesn't matter, but touching a single existing byte does).
Format: first row of a question carries `Category,Question,Answer,Kick`;
every following row (blank Category/Question) is one more paragraph/beat
of that answer. Answer text is a short *cue* (e.g. `(intro) calling
Hansamm about the X20 chair from a flyer`), not the full script — the full
verbatim text goes in the doc-text file instead (step 4). Compose your own
short cues and 2-4 short kick phrases per beat, matching the voice and
length of neighboring rows already in the file — don't copy the doc's
prose verbatim into the CSV.

Do the append with a small Python script using the `csv` module
(`quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n"`) rather than editing
the file by hand — the existing file uses CRLF line endings and has no
trailing newline; get this wrong and `git diff` will show every existing
line as changed. Read the existing file as raw bytes, write it back
unmodified, then append the new rows' bytes. After writing, run `git diff
--stat` and `git diff` and confirm the diff is *pure addition* — no
existing line touched, no "\ No newline at end of file" turning into a
real content change beyond the newline itself.

### 4. Save the doc script text

Append the new questions' full verbatim text (tags normalized to match the
regex from step 2, e.g. `Q10-4.` → `10-4.`) to the relevant
`data/docs/<n>-<slug>.txt` file, or create a new file for a brand-new
topic. These files carry a UTF-8 BOM and CRLF-normalize on read (via
`utf-8-sig` in `parse_docs.py`) — match the existing file's encoding when
appending (open in `"ab"` / bytes mode) rather than rewriting the whole
file, to avoid silently dropping the BOM or the file's existing questions.

### 5. Wire up new topics/questions in parse_source.py

- New topic: add an entry to `TOPIC_SCRIPT_URLS` (topic name → the Doc's
  `viewUrl` or `https://docs.google.com/document/d/<id>/edit`).
- Every new question tag: add a short (2-6 word) gist to `QUESTION_LABELS`,
  keyed by tag. Without this the node just falls back to showing its raw
  tag, which works but is less readable — cheap enough to always fill in.

### 6. Regenerate and rebuild

```
python3 scripts/parse_source.py   # -> data/forest.json
python3 scripts/build.py          # -> mindmap.html, index.html
```

`parse_source.py` prints warnings to stderr for any question with no
matching doc script, or any remaining untranslated Korean — treat both as
things to fix before moving on, not things to ignore.

### 7. Test before deploying

Rebuild a scratchpad test copy (copy `templates/mindmap.template.html` +
`data/forest.json` into the scratchpad, run its local `rebuild.py`, swap
the CDN d3 script tag for `node_modules/d3/dist/d3.min.js` since the CDN is
blocked in this sandbox) and run the full existing Playwright regression
suite (`verify_*.mjs` in the scratchpad) — batch it into groups run via
`Bash` with `run_in_background`/`Monitor` rather than one long foreground
call, since the full suite comfortably exceeds a single tool call's
timeout. Also write (or reuse) a small targeted check that the grove lists
every topic including the new one(s), the new question tags are all
present with their scripts loaded from the doc text, and — critically — an
existing topic (e.g. Movie) still shows exactly its original question
count, to positively confirm nothing existing regressed.

### 8. Back up the live sheet, then push the new CSV to Drive

No Drive tool here can edit a Sheet's cells directly — only whole-file
create/copy/rename/move. So:

1. Ensure the `backup/` subfolder under the Speaking Log folder exists
   (create it once if missing — check first, don't create duplicates).
2. `copy_file` the CURRENT live `"(1급) Mind map"` sheet into `backup/`
   with a dated title (e.g. `(1급) Mind map (백업 ~YYYY-MM-DD, <short
   reason>)`) — this is the safety copy, taken *before* anything about the
   live file changes.
3. Rename the (now-superseded) live sheet to indicate that (e.g. `(1급)
   Mind map (구버전 — <reason>, 삭제해도 됨)` — "구버전" = old version,
   "삭제해도 됨" = safe to delete, since nothing here can delete it for the
   user) and move it into `backup/` too via `update_file`'s `parentId`.
   Every backup — the dated copy and the renamed original alike — belongs
   in `backup/`, not loose in the main folder.
4. `create_file` the new merged `data/opic-source.csv` content as a new
   Google Sheet titled `"(1급) Mind map"` directly in the Speaking Log
   folder (`contentMimeType: "text/csv"`, `disableConversionToGoogleType:
   false` so it converts to a real Sheet). Pass the CSV as `textContent`
   built from the actual current file content (don't retype it from
   memory) — for a file this size, read it once and pass it through
   exactly, then verify by downloading the new sheet's content back
   (`exportMimeType: "text/csv"`) and confirming it ends with the exact
   last row you expect, so a silent truncation on upload doesn't go
   unnoticed.

### 9. Commit, push, deploy

Commit all changed repo files (`data/opic-source.csv`, the doc-text
file(s), `scripts/parse_source.py`, `scripts/parse_docs.py` if touched,
`data/forest.json`, `mindmap.html`, `index.html`) with a message describing
what was added. Push to the branch this session is working on. Then
republish the Artifact (same `url` as before, if one exists for this
project) so the live artifact reflects the update too — the git push alone
covers GitHub Pages (`jmseo16.github.io`); the Artifact needs its own
republish call.

## Hard constraints

- **Never** modify or remove an existing row in `opic-source.csv`, an
  existing paragraph in a doc-text file, or an existing entry in
  `TOPIC_SCRIPT_URLS`/`QUESTION_LABELS`. Every change in this workflow is
  an addition. Verify this with `git diff` before committing — a diff with
  any `-` line beyond a trailing-newline artifact means something existing
  got touched; stop and figure out why before proceeding.
- **Never** leave a Drive backup loose in the main Speaking Log folder —
  every backup (dated copy or renamed superseded original) goes in
  `backup/`.
- **Never** skip the regression suite before pushing — this repo has an
  existing Playwright suite specifically to guard against exactly the kind
  of silent breakage a data-pipeline change could cause.
