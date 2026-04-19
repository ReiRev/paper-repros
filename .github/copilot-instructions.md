# GitHub Copilot Instructions — paper-repros

This repository contains research paper reproductions as self-contained Jupyter notebooks.

## Notebook conventions

- Each notebook lives at `notebook/<genre>/<subgenre>/<year>-<kebab-case-title>.ipynb`
- Every notebook is fully self-contained: no imports from repo-local files
- Dependencies: `numpy`, `matplotlib`, stdlib only

## When writing notebook code

### Structure

Every paper notebook follows this cell order:
1. Title + citation (markdown)
2. Algorithm explanation with equations (markdown, detailed)
3. Assumptions table for every underspecified paper detail (markdown)
4. Imports, constants, shared data types (code — minimal shared setup only)
5. Per-figure/section: markdown explanation → helper functions + run → plot cell(s)
6. Summary table (markdown)

**Cell granularity is critical:**
- Split cells frequently — one logical action per cell
- **One `plt.show()` per cell** — never put two independent figures in the same cell
- Separate "run expensive trial" from "plot result" when computation takes > a few seconds
- Do NOT collect all functions in a large setup cell — define each helper near its first use
- Render inline mathematics in markdown with `$ ... $` and display mathematics with `$$ ... $$`
- Never use inline backticks or fenced code blocks for mathematical notation; reserve backticks for code, paths, commands, and literal strings

### Implementation

```python
# Style
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8-whitegrid")

# RNG — always fixed seed for reproducibility
rng = np.random.default_rng(0)

# Config objects — frozen dataclass
@dataclass(frozen=True)
class TrialConfig:
    mode: str
    load: float
    steps: int = 10_000
    seed: int = 0
```

### Colormaps

Use `cmap="jet"` for:
- Node utilisation heatmaps
- Policy summary density plots
- Any 2D spatial data visualisation

Example:
```python
im = ax.imshow(grid, cmap="jet", vmin=0, vmax=vmax, interpolation="nearest")
plt.colorbar(im, ax=list(axes), label="Route count through node")
```

### Assumptions

When a paper detail is unspecified, add it to the assumptions table and document it
in code with a named constant:

```python
DEFAULT_SETTLE_TIME = 5_000   # paper says "after settling" without defining it
PAPER_SHORT_PATH_TIE_BREAK = ("W", "E", "N", "S")  # not stated; chosen to match Figure 3
```

### Plotting helpers

Keep plotting code **inline** in the figure cell. Do not create notebook-level plotting
helper functions. This makes each figure cell independently readable.

### Expensive cells

For multi-trial sweeps (e.g., 19 seeds × 9 load levels), add a print statement at the
start of the cell:

```python
print("Running Figure 4 load sweep (this may take several minutes)...")
```

## Comments and docstrings

Add a docstring to every function. For non-trivial code, add inline comments explaining
the *why*: algorithm choices, paper-specific constants, non-obvious invariants.

Do not comment basic operations — the reader knows Python and standard libraries.

```python
def simulate_trial(config: TrialConfig, topology: Topology | None = None) -> TrialResult:
    """Run one simulation trial and return all deliveries and the learned policy.

    Uses the topology's shortest-path as a fallback for mode='shortest-path'.
    Q-values are initialised to 0 for all reachable (node, dest, neighbour) triples
    except self-loops (inf) and direct-delivery edges (0 regardless of init_q).
    """
    ...

# active_packet_limit caps the queue to prevent unbounded memory use under high load
if active_packets >= config.active_packet_limit:
    break
```

## Git discipline

Always check `git status` before starting. Commit after every logical change so that
bad results can be reverted without losing unrelated work.

## When editing existing notebooks

- Prefer editing the implementation cell directly rather than adding new cells
- Keep helper functions near the cell that first uses them
- Do not move all utilities to a single setup cell
- Preserve the paper-comparison outputs (L1 error, printed grids)

## File naming

Always kebab-case:
- `1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach.ipynb`
- Genre and subgenre directories: `network/routing/`, `vision/segmentation/`, etc.

## Verification command

```bash
mkdir -p /tmp/paper-repros-notebooks && \
poetry run jupyter nbconvert --to notebook --execute \
  --output-dir /tmp/paper-repros-notebooks \
  --ExecutePreprocessor.timeout=0 \
  <notebook path>
```
