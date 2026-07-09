# Contributing

The best PRs here carry knowledge, not code.

## The skills flywheel

Three files in `.claude/skills/` are the product: design standards, chart
XML recipes, and twb grammar. Someone verified every rule in them against
a live Tableau render before writing it down. Keep that bar:

1. **Found new grammar?** A chart type, a formatting trick, an action
   pattern. Add it to the right skill with the evidence: what you built,
   what rendered, what broke. "Verified live" beats "should work."
2. **New chart recipe?** It has to pass the specimen book. Add your chart
   to `tools/build_specimen.py`, run the generate → validate → lint →
   render cycle, and drop the render in your PR.
3. **Design standards** hold opinions on purpose. If your taste differs,
   fork the skill. That is the design. PRs should add rules most people
   would defend (accessibility, alignment, labeling), not swap the palette.
4. **New lint check?** Ship it with a passing case and a failing case in
   the PR description.

## Ground rules

- Leave downloaded third-party workbooks and their extracts out of git.
  The miners rebuild them locally (see `knowledge/README.md`).
- Back every grammar claim with a source: a corpus example, or a render.
- Run `validate_twb.py` and `lint_design.py` on any twb you touch.
