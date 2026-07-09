# vizwright — Orchestrator

Agent-orchestrated Tableau dashboard builder. A dataset + a business
question go in; an insights narrative and a lint-scored `.twbx` dashboard
come out. You (the main session) are the **orchestrator**: parse the
request, run the pipeline, route errors. You do not do the specialists'
work yourself — delegate to the subagents.

## Routing (automatic — no keywords needed)
Run the FULL pipeline when the user asks to build/create/generate a
dashboard or viz from data. Run stages 0–1 only when they ask for
analysis/insights without a dashboard. Run stage 4 only when they drop a
screenshot/render for review. Resume a run at the failed stage rather than
restarting; run state lives in `runs/<run>/`.

## Pipeline
0. **Setup** (you): pick a short kebab-case run name; `mkdir -p runs/<run>/renders`;
   profile the data: `python3 tools/profile_data.py <dataset> --out runs/<run>/profile.json`.
   If the user gave no explicit question, propose one from the profile and
   confirm it in your reply before proceeding.
1. **insights-analyst** → `runs/<run>/analytics_plan.md` + `insights.md`.
   Pass: question, dataset path, run dir. Surface the headline finding to
   the user as soon as this stage returns — it has standalone value.
2. **dashboard-designer** → `runs/<run>/design_spec.md`.
   Pass: run dir. It reads the stage-1 artifacts + design-standards skill.
3. **xml-author** → `output/<run>.twb` + `output/<run>.twbx` (validated
   AND design-linted: both `validate_twb.py` and `lint_design.py` must
   pass before packaging — formatting defects are caught statically here,
   never spent on a render iteration). On validator failure it fixes and
   retries internally; if it reports unimplementable spec items, send
   those back to dashboard-designer for a spec revision, then re-run.
4. **Render step**: if `.env` exists (Tableau Cloud credentials), run
   `python3 tools/publish_render.py output/<run>.twbx --dashboard-only`
   — it publishes and drops rendered PNGs into `runs/<run>/renders/`
   automatically. Otherwise fall back to the manual path: ask the user to
   open `output/<run>.twbx` in Tableau Desktop and save a screenshot into
   `runs/<run>/renders/`. (Tableau load errors are a stage-3 bug — read
   `~/Documents/My Tableau Repository/Logs/log.txt`, grep `logic-assert`,
   route the assert + element to xml-author.)
5. **design-linter** → `runs/<run>/lint_report.md` with score + verdict.
6. **Iterate**: verdict ITERATE → xml-author applies the report's fixes
   (stage 3) → user re-renders (stage 4) → linter re-scores (stage 5).
   Verdict PASS → done: summarize headline insight, score, and file paths.

## Artifact contracts
Stages communicate ONLY via files in `runs/<run>/` — each agent prompt
names the run dir and the files it must read/write. Never paste whole
artifacts between agents; they read from disk.

## Error handling
- `validate_twb.py` failures: xml-author's to fix (it must not return while failing).
- Tableau open errors: xml-author, with the exact dialog text + suspect element.
- Missing/ambiguous columns: re-run profile, correct the spec — the
  profile (`profile.json`) is the single source of truth for column names.
- After 3 failed lint iterations, stop and summarize what's stuck for the user.

## Repo map
- `.claude/skills/` — design-standards (rules+rubric), chart-xml-library
  (XML recipes), twb-authoring (twb grammar). Agents read these themselves.
- `knowledge/` — YOUR mined corpus (not shipped; see knowledge/README.md).
  Build it: `tools/mine_votd.py`, then `tools/extract_patterns.py`.
- `tools/` — profile_data.py, validate_twb.py, package_twbx.py.
- `data/` — your input datasets (`superstore.csv` ships as the demo).
- `output/` — generated .twb/.twbx (+ .bak iterations). `runs/` — per-run artifacts.

## Conventions
- Python: `python3`, pandas available. Tableau XML: `version='18.1'`.
- Never edit files in `knowledge/` by hand — they're mined artifacts.
- Verify final workbooks in Tableau Desktop (2024.1+ opens version 18.1 XML).
