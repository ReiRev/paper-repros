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
- In long notebooks, define helper functions close to the cells that first use them instead of collecting the entire implementation in one setup cell.
- Keep plotting code inline in the figure cells. Do not add notebook-only plotting helper functions.
- Prefer deterministic seeds for representative single-run figures.
- Keep filenames in kebab-case.

## Current 1993 Routing Paper

- Notebook generator:
  `scripts/generate_packet_routing_1993_notebook.py`
- Notebook:
  `notebook/network/routing/1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach.ipynb`

## Commands

- Install dependencies:
  `poetry install --with dev`
- Regenerate the notebook:
  `poetry run python scripts/generate_packet_routing_1993_notebook.py`
- Execute the notebook for verification:
  `mkdir -p /tmp/paper-repros-notebooks && poetry run jupyter nbconvert --to notebook --execute --output-dir /tmp/paper-repros-notebooks --ExecutePreprocessor.timeout=0 notebook/network/routing/1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach.ipynb`
  Note: the full evaluation cells are intentionally expensive and may take several minutes.
- Install git hooks:
  `poetry run pre-commit install`
- Run all hooks manually:
  `poetry run pre-commit run --all-files`
