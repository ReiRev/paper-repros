# /repro — Reproduce a paper as a self-contained notebook

Reproduce all figures and experiments from a research paper PDF.

## Usage

```
/repro [pdf filename or path]
```

If no argument is given, list the PDFs in `pdf/` and ask which one to reproduce.

## What to produce

Create a single self-contained Jupyter notebook at:

```
notebook/<genre>/<subgenre>/<year>-<kebab-case-title>.ipynb
```

Derive `<genre>`, `<subgenre>`, and `<year>` from the paper.
Use kebab-case for all path components.

## Notebook requirements

### Must include

1. **Title cell** — paper title, authors, venue/year, one-sentence summary.

2. **Algorithm explanation cell** — detailed markdown:
   - Core mathematical formulation (equations rendered with LaTeX-style backtick blocks)
   - Intuition for why the algorithm works
   - What makes it novel vs prior work
   - Any variants described in the paper

3. **Assumptions cell** — markdown table listing every underspecified detail with the assumption used. Examples of things to surface: tie-break rules, hyperparameter values not in the paper, initialisation strategies, settling criteria, traffic patterns, topology details.

4. **Implementation** — pure Python using only `numpy`, `matplotlib`, and stdlib.
   No repo-local modules. **Do NOT collect all functions in one large setup cell.**
   Define each helper function in the same cell where it is first used, or in the
   code cell immediately before that figure's section.

5. **Cell granularity** — split cells frequently so users can execute one at a time:
   - **One `plt.show()` per cell** — never group multiple independent figures in a single cell.
   - Separate "run experiment" from "plot result" where it makes sense
     (e.g. expensive trial in one cell, `plt.show()` in the next).
   - Each figure section = markdown explanation cell + one or more code cells.

6. **One markdown cell per figure** — precedes the code, explains:
   - What the figure shows and why it matters
   - Expected qualitative result
   - Any assumptions specific to that figure

7. **Summary cell** — markdown table: figure/section → what it shows → status.

### Figures and colormaps

- Use `jet` colormap for heatmaps and density visualisations.
- Keep plotting code inline in its figure cell; no shared plotting helpers.
- Use `plt.style.use("seaborn-v0_8-whitegrid")` at the top of the notebook.
- Use `np.random.default_rng(seed)` with fixed seeds; prefer `seed=0` for single runs.

### Comments and docstrings

Add a docstring to every function. For non-trivial code blocks, add inline comments
explaining the *why* — algorithm choices, paper-specific constants, non-obvious
invariants. Do not comment basic Python or numpy operations; assume the reader
knows the language and standard libraries.

### Assumptions documentation

For every detail the paper leaves unspecified, add an explicit row to the assumptions table. If a parameter appears only in a referenced technical report, note the discrepancy. Never silently fill in a gap.

### Self-containment

The notebook must execute from top to bottom with `poetry run jupyter nbconvert --to notebook --execute` without any import from repo-local files. All utilities must be defined inside the notebook.

## Workflow

1. Check `git status` before starting.
2. Read the PDF fully — extract all figures, algorithms, parameter values, metrics, and experimental setup.
3. Draft the assumptions table before writing any code.
4. Write the implementation; verify it can reproduce the policy summary or equivalent sanity-check figure first.
5. Reproduce figures in order, cheapest first.
6. Run the expensive multi-trial sweeps last.
7. Execute the full notebook to confirm no errors.
8. Commit. If anything is wrong the user will revert the commit.

## Verification

After generating the notebook, run:

```bash
mkdir -p /tmp/paper-repros-notebooks && \
poetry run jupyter nbconvert --to notebook --execute \
  --output-dir /tmp/paper-repros-notebooks \
  --ExecutePreprocessor.timeout=0 \
  <notebook path>
```

Report the exit code and any cell errors.
