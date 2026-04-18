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

4. **Implementation cell(s)** — pure Python using only `numpy`, `matplotlib`, and stdlib. No repo-local modules. Define helper functions close to the cells that first use them.

5. **One cell per figure** — reproduce every figure in the paper. Each figure cell must be preceded by a markdown cell explaining:
   - What the figure shows
   - What the expected qualitative result is
   - Any assumptions specific to that figure

6. **Summary cell** — markdown table with: figure/section → what it shows → reproduction status.

### Figures and colormaps

- Use `jet` colormap for any heatmap or density visualisation you create.
- Keep all plotting code inline in the figure cell; no shared plotting helpers.
- Use `plt.style.use("seaborn-v0_8-whitegrid")` as the default style.
- Use `np.random.default_rng(seed)` with a fixed seed for all stochastic elements.
- Prefer `seed=0` for single representative figures.

### Assumptions documentation

For every detail the paper leaves unspecified, add an explicit row to the assumptions table. If a parameter appears only in a referenced technical report, note the discrepancy. Never silently fill in a gap.

### Self-containment

The notebook must execute from top to bottom with `poetry run jupyter nbconvert --to notebook --execute` without any import from repo-local files. All utilities must be defined inside the notebook.

## Workflow

1. Read the PDF fully — extract all figures, algorithms, parameter values, metrics, and experimental setup.
2. Draft the assumptions table before writing any code.
3. Write the implementation; verify it can reproduce the policy summary or equivalent sanity-check figure first.
4. Reproduce figures in order, cheapest first.
5. Run the expensive multi-trial sweeps last.
6. Execute the full notebook to confirm no errors.

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
