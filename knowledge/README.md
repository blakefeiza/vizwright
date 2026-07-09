# knowledge/ is yours to fill

This folder ships almost empty on purpose. The agents learn from real
workbooks you feed them, and downloaded Tableau Public content belongs to
its authors. So you build your own corpus locally instead of cloning
someone else's:

```bash
# 1. Pull the recent Viz of the Day catalog (metadata + classification)
python3 tools/mine_votd.py --max 300

# 2. Download ~20 business-type winners and extract per-chart XML patterns
python3 tools/extract_patterns.py --count 20
```

That fills `votd/` (catalog and workbooks) and `xml-patterns/` (raw
worksheet, dashboard, and datasource fragments the XML author reads when a
recipe falls short).

Better still, add your own workbooks. Drop any `.twb` or `.twbx` you
admire into `interactivity/` or a folder you name, then ask the agent to
mine it. That is how the set-action, beeswarm, and dark-map grammar in
[LEARNINGS.md](interactivity/LEARNINGS.md) got here. Your company's best
dashboard is the best training data you own.

Everything here is raw source. The distilled, shareable result lives in
`.claude/skills/`. That is what PRs improve.
