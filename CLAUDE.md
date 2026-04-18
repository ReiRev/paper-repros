# Paper Repros

## Scope

- This repository stores paper reproductions primarily as self-contained notebooks.
- Prefer keeping the implementation inside the notebook unless the user explicitly asks for extracted modules or shared utilities.

## Layout

- Notebook generators: `scripts/`
- Generated notebooks: `notebook/<genre>/<subgenre>/<year>-<title>.ipynb`

## Required Reproduction Rules

- Reproduce the paper's evaluation, not only the algorithm.
- If the paper leaves out a parameter, schedule, tie-break rule, or metric definition, state that explicitly in the notebook and document the assumption used.
- Write notebook prose and explanatory markdown in English unless the user explicitly asks for another language.
- Keep each paper notebook self-contained by default. Avoid runtime dependencies on repo-local modules unless the user explicitly wants shared code.
- Define helper functions in the same cell where they are first used, or in the code cell immediately before that section. Never collect all functions in one large setup cell.
- Split cells frequently so users can execute the notebook one cell at a time. One `plt.show()` per cell — never group independent figures. Separate expensive computation from plotting when computation takes more than a few seconds.
- Keep plotting code inline in the figure cells. Do not add notebook-only plotting helper functions.
- Use `jet` colormap for heatmaps and density visualisations.
- Add docstrings to all functions and comments to non-obvious code blocks. Assume users know Python and standard libraries (numpy, matplotlib) — skip comments on basic operations. Focus on the *why*: algorithm choices, paper-specific constants, non-obvious invariants.
- Prefer deterministic seeds for representative single-run figures.
- Keep filenames in kebab-case.
- Before starting any task, check `git status`. Commit after every logical change so that bad changes can be reverted cleanly.

## Current 1993 Routing Paper

- Notebook:
  `notebook/network/routing/1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach.ipynb`
- PDF:
  `pdf/NIPS-1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach-Paper.pdf`

## Commands

- Install dependencies:
  `poetry install --with dev`
- Execute the notebook for verification:
  `mkdir -p /tmp/paper-repros-notebooks && poetry run jupyter nbconvert --to notebook --execute --output-dir /tmp/paper-repros-notebooks --ExecutePreprocessor.timeout=0 notebook/network/routing/1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach.ipynb`
  Note: the full evaluation cells are intentionally expensive and may take several minutes.
- Install git hooks:
  `poetry run pre-commit install`
- Run all hooks manually:
  `poetry run pre-commit run --all-files`
