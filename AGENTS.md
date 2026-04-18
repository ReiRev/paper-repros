# Agent Instructions — paper-repros

This repository stores research paper reproductions as self-contained Jupyter notebooks.

## Repository layout

```
pdf/                          source PDFs
notebook/<genre>/<subgenre>/  generated notebooks
  <year>-<kebab-case-title>.ipynb
CLAUDE.md                     project-level instructions
AGENTS.md                     this file
```

## Primary task: reproduce a paper

Given a PDF in `pdf/`, produce a notebook at the path above that reproduces every
figure and experiment in the paper.

### Step 1 — Read the paper

Read the entire PDF. Extract:
- All figures: number, caption, axes labels, expected qualitative shape
- All algorithms: pseudocode, update equations, initialisation
- All parameter values mentioned anywhere in the text or footnotes
- All experimental setup details: network topology, trial counts, load ranges, metrics

### Step 2 — Draft the assumptions table

List every detail the paper leaves unspecified. For each one, state the assumption used.
Do not silently fill in gaps — every assumption must appear in the notebook.

Common underspecified details:
- Tie-break rules for deterministic algorithms
- Exact hyperparameter values (check referenced technical reports)
- Packet/event limits
- Definition of "converged" or "after settling"
- Traffic generation process
- Topology edge list when only a figure is given

### Step 3 — Write the notebook

**Structure (one markdown cell + one code cell per figure):**

```
# Title (markdown)
## Algorithm explanation (markdown) — detailed, include equations
## Assumptions (markdown) — table of underspecified details
## Implementation (code) — all Python utilities, inline
## Figure 1 explanation (markdown)
## Figure 1 (code)
...
## Summary (markdown)
```

**Implementation rules:**
- Pure Python: only `numpy`, `matplotlib`, stdlib
- No imports from repo-local files
- In notebook markdown, render display mathematics with `$$ ... $$`; never put mathematical formulas inside fenced code blocks.
- **Do NOT put all functions in one large setup cell.** Define each helper function
  in the cell where it is first used, or in the code cell immediately before that section.
- Plotting code inline in figure cells; no shared plotting helpers
- `plt.style.use("seaborn-v0_8-whitegrid")` at the top of the notebook
- Fixed seeds via `np.random.default_rng(seed)` — prefer `seed=0` for single runs
- Add a docstring to every function. Add inline comments to non-obvious code blocks
  (algorithm choices, paper-specific constants, non-obvious invariants). Skip comments
  on basic Python/numpy operations — assume the reader knows the language.

**Cell granularity rules:**
- Split cells frequently — users execute the notebook one cell at a time
- **One `plt.show()` per cell** — never group multiple independent figures
- Separate expensive computation ("run trial") from display ("plot result")
  so users can re-plot without re-running a long simulation

**Figure rules:**
- Reproduce every figure in the paper
- Use `jet` colormap for heatmaps and node-utilisation density plots
- Label axes and add colorbars where appropriate
- Include a difference/error heatmap when comparing reproduced vs paper values

### Step 4 — Verify

Execute the full notebook:

```bash
mkdir -p /tmp/paper-repros-notebooks
poetry run jupyter nbconvert --to notebook --execute \
  --output-dir /tmp/paper-repros-notebooks \
  --ExecutePreprocessor.timeout=0 \
  <notebook path>
```

Fix any errors. Report execution status.

## Code style

- Python 3.12+, type annotations where helpful
- Kebab-case for all filenames and paths
- No comments that explain *what* code does; only comments for non-obvious *why*
- No docstrings on small helpers
- `dataclass(frozen=True)` for configuration objects

## Git discipline

- Check `git status` before starting any task.
- Commit after every logical change. Small, reversible commits let the user revert
  a bad change without losing unrelated work.

## What not to do

- Do not create shared utility modules; keep everything inside the notebook
- Do not add a `scripts/` generator; write the notebook directly
- Do not guess parameter values; document assumptions explicitly
- Do not skip figures because they are expensive; mark them with a runtime warning instead
