"""Generate the notebook for the 1993 Q-routing paper reproduction."""

from __future__ import annotations

from pathlib import Path
import textwrap

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "notebook"
    / "network"
    / "routing"
    / "1993-packet-routing-in-dynamically-changing-networks-a-reinforcement-learning-approach.ipynb"
)
REPRO_SOURCE = '''
"""Reproduction utilities for Boyan and Littman (NIPS 1993) Q-routing."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import argparse
import math
import statistics
from typing import Literal

import numpy as np


Mode = Literal["q-routing", "shortest-path", "full-echo"]
TrafficPattern = Literal["uniform", "upper-lower", "left-right"]


FIGURE2_LOW_LOAD = 1.0
FIGURE2_HIGH_LOAD = 2.5
DEFAULT_SETTLE_TIME = 5_000
DEFAULT_STEPS = 10_000
DEFAULT_ACTIVE_PACKET_LIMIT = 1_000
PAPER_SHORT_PATH_TIE_BREAK = ("W", "E", "N", "S")

PAPER_POLICY_SUMMARY_SHORTEST = np.array(
    [
        [164, 131, 117, 116, 125, 155],
        [207, 45, 54, 54, 43, 199],
        [286, 344, 570, 573, 330, 278],
        [140, 196, 249, 255, 185, 140],
        [95, 143, 146, 154, 149, 108],
        [45, 76, 58, 58, 63, 41],
    ],
    dtype=int,
)

PAPER_POLICY_SUMMARY_Q_ROUTING = np.array(
    [
        [384, 392, 396, 396, 393, 387],
        [375, 102, 59, 54, 82, 377],
        [394, 292, 258, 269, 246, 383],
        [262, 248, 144, 227, 201, 217],
        [170, 148, 93, 160, 141, 162],
        [79, 105, 75, 108, 121, 74],
    ],
    dtype=int,
)


@dataclass(frozen=True)
class Topology:
    name: str
    coordinates: dict[int, tuple[int, int]]
    neighbors: tuple[tuple[int, ...], ...]

    @property
    def node_count(self) -> int:
        return len(self.coordinates)

    @property
    def edges(self) -> tuple[tuple[int, int], ...]:
        edges: set[tuple[int, int]] = set()
        for node, nbrs in enumerate(self.neighbors):
            for neighbor in nbrs:
                if node < neighbor:
                    edges.add((node, neighbor))
        return tuple(sorted(edges))

    def to_grid(self, values: np.ndarray) -> np.ndarray:
        grid = np.zeros((6, 6), dtype=values.dtype)
        for node, (row, col) in self.coordinates.items():
            grid[row, col] = values[node]
        return grid

    def direction(self, source: int, neighbor: int) -> str:
        source_row, source_col = self.coordinates[source]
        neighbor_row, neighbor_col = self.coordinates[neighbor]
        if neighbor_row < source_row:
            return "N"
        if neighbor_row > source_row:
            return "S"
        if neighbor_col < source_col:
            return "W"
        if neighbor_col > source_col:
            return "E"
        raise ValueError(f"source={source} and neighbor={neighbor} are identical")


@dataclass(frozen=True)
class TopologyEvent:
    at: int
    remove_edges: tuple[tuple[int, int], ...] = ()
    add_edges: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class TrialConfig:
    mode: Mode
    load: float
    steps: int = DEFAULT_STEPS
    learning_rate: float = 0.5
    transmission_time: int = 1
    active_packet_limit: int = DEFAULT_ACTIVE_PACKET_LIMIT
    settle_time: int = DEFAULT_SETTLE_TIME
    initial_q_value: float = 0.0
    tie_break_order: tuple[str, ...] = PAPER_SHORT_PATH_TIE_BREAK
    traffic_schedule: tuple[tuple[int, TrafficPattern], ...] = ((0, "uniform"),)
    load_schedule: tuple[tuple[int, float], ...] | None = None
    topology_events: tuple[TopologyEvent, ...] = ()
    seed: int = 0

    def __post_init__(self) -> None:
        if self.transmission_time != 1:
            raise ValueError("This reproduction currently supports only transmission_time=1.")


@dataclass
class TrialResult:
    config: TrialConfig
    topology: Topology
    deliveries: np.ndarray
    q_values: np.ndarray | None
    policy: np.ndarray
    shortest_path_policy: np.ndarray
    distances: np.ndarray

    def mean_delivery_time(self, start_time: int | None = None) -> float:
        start = self.config.settle_time if start_time is None else start_time
        tail = self.deliveries[self.deliveries[:, 0] >= start, 1]
        return float(np.mean(tail)) if tail.size else float("nan")

    def binned_delivery_curve(self, bin_size: int = 100) -> tuple[np.ndarray, np.ndarray]:
        bin_starts = np.arange(0, self.config.steps, bin_size, dtype=int)
        means = np.full(bin_starts.shape, np.nan, dtype=float)
        delivered_at = self.deliveries[:, 0]
        latencies = self.deliveries[:, 1]
        for index, start in enumerate(bin_starts):
            end = start + bin_size
            mask = (delivered_at >= start) & (delivered_at < end)
            if np.any(mask):
                means[index] = float(np.mean(latencies[mask]))
        return bin_starts, means

    def policy_counts(
        self,
        *,
        include_source: bool = True,
        include_destination: bool = False,
        max_hops: int = 64,
    ) -> np.ndarray:
        return policy_route_counts(
            self.policy,
            include_source=include_source,
            include_destination=include_destination,
            max_hops=max_hops,
        )


def build_irregular_grid_topology() -> Topology:
    coordinates = {row * 6 + col: (row, col) for row in range(6) for col in range(6)}
    adjacency: dict[int, list[int]] = {node: [] for node in coordinates}

    def add_edge(a: tuple[int, int], b: tuple[int, int]) -> None:
        left = a[0] * 6 + a[1]
        right = b[0] * 6 + b[1]
        adjacency[left].append(right)
        adjacency[right].append(left)

    for col in range(5):
        add_edge((0, col), (0, col + 1))
        add_edge((2, col), (2, col + 1))

    add_edge((1, 1), (1, 2))
    add_edge((1, 3), (1, 4))

    for left, right in (
        ((3, 0), (3, 1)),
        ((3, 1), (3, 2)),
        ((3, 3), (3, 4)),
        ((3, 4), (3, 5)),
        ((4, 0), (4, 1)),
        ((4, 1), (4, 2)),
        ((4, 3), (4, 4)),
        ((4, 4), (4, 5)),
        ((5, 0), (5, 1)),
        ((5, 1), (5, 2)),
        ((5, 3), (5, 4)),
        ((5, 4), (5, 5)),
    ):
        add_edge(left, right)

    for row in range(5):
        add_edge((row, 0), (row + 1, 0))
        add_edge((row, 5), (row + 1, 5))

    for row in range(1, 5):
        for col in (1, 2, 3, 4):
            add_edge((row, col), (row + 1, col))

    neighbors = tuple(tuple(sorted(adjacency[node])) for node in range(len(coordinates)))
    return Topology(
        name="irregular-6x6-grid",
        coordinates=coordinates,
        neighbors=neighbors,
    )


def shortest_path_distances(topology: Topology) -> np.ndarray:
    node_count = topology.node_count
    distances = np.full((node_count, node_count), fill_value=node_count + 1, dtype=int)
    for source in range(node_count):
        distances[source, source] = 0
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for neighbor in topology.neighbors[node]:
                if distances[source, neighbor] > distances[source, node] + 1:
                    distances[source, neighbor] = distances[source, node] + 1
                    queue.append(neighbor)
    return distances


def shortest_path_policy(
    topology: Topology,
    distances: np.ndarray,
    *,
    tie_break_order: tuple[str, ...] = PAPER_SHORT_PATH_TIE_BREAK,
) -> np.ndarray:
    order_index = {direction: index for index, direction in enumerate(tie_break_order)}
    policy = np.full(distances.shape, fill_value=-1, dtype=int)
    for source in range(topology.node_count):
        for destination in range(topology.node_count):
            if source == destination:
                continue
            candidates = [
                neighbor
                for neighbor in topology.neighbors[source]
                if distances[neighbor, destination] == distances[source, destination] - 1
            ]
            candidates.sort(
                key=lambda neighbor: (
                    order_index[topology.direction(source, neighbor)],
                    neighbor,
                )
            )
            policy[source, destination] = candidates[0]
    return policy


def policy_route_counts(
    policy: np.ndarray,
    *,
    include_source: bool = True,
    include_destination: bool = False,
    max_hops: int = 64,
) -> np.ndarray:
    node_count = policy.shape[0]
    counts = np.zeros(node_count, dtype=int)
    for source in range(node_count):
        for destination in range(node_count):
            if source == destination:
                continue
            node = source
            if include_source:
                counts[node] += 1
            seen = {node}
            for _ in range(max_hops):
                node = int(policy[node, destination])
                if node == -1:
                    break
                if node == destination:
                    if include_destination:
                        counts[node] += 1
                    break
                counts[node] += 1
                if node in seen:
                    break
                seen.add(node)
    return counts


def _build_mutable_neighbors(topology: Topology, tie_break_order: tuple[str, ...]) -> list[list[int]]:
    order_index = {direction: index for index, direction in enumerate(tie_break_order)}
    mutable_neighbors = [list(neighbors) for neighbors in topology.neighbors]
    for node, neighbors in enumerate(mutable_neighbors):
        neighbors.sort(
            key=lambda neighbor: (order_index[topology.direction(node, neighbor)], neighbor)
        )
    return mutable_neighbors


def _apply_topology_event(
    neighbors: list[list[int]],
    event: TopologyEvent,
    topology: Topology,
    q_values: np.ndarray | None,
) -> None:
    for left, right in event.remove_edges:
        if right in neighbors[left]:
            neighbors[left].remove(right)
        if left in neighbors[right]:
            neighbors[right].remove(left)
        if q_values is not None:
            q_values[left, :, right] = np.inf
            q_values[right, :, left] = np.inf

    for left, right in event.add_edges:
        if right not in neighbors[left]:
            neighbors[left].append(right)
        if left not in neighbors[right]:
            neighbors[right].append(left)
        neighbors[left].sort()
        neighbors[right].sort()
        if q_values is not None:
            q_values[left, :, right] = np.where(
                np.arange(topology.node_count) == left,
                np.inf,
                0.0,
            )
            q_values[right, :, left] = np.where(
                np.arange(topology.node_count) == right,
                np.inf,
                0.0,
            )


def _scheduled_value(step: int, schedule: tuple[tuple[int, object], ...]) -> object:
    current = schedule[0][1]
    for change_at, value in schedule:
        if step < change_at:
            break
        current = value
    return current


def _sample_packet_pair(
    rng: np.random.Generator,
    pattern: TrafficPattern,
    topology: Topology,
) -> tuple[int, int]:
    nodes = np.arange(topology.node_count)
    rows = np.array([topology.coordinates[node][0] for node in nodes], dtype=int)
    cols = np.array([topology.coordinates[node][1] for node in nodes], dtype=int)

    if pattern == "uniform":
        source = int(rng.integers(0, topology.node_count))
        destination = int(rng.integers(0, topology.node_count - 1))
        if destination >= source:
            destination += 1
        return source, destination

    if pattern == "upper-lower":
        upper = nodes[rows <= 2]
        lower = nodes[rows >= 3]
        if rng.random() < 0.5:
            return int(rng.choice(upper)), int(rng.choice(lower))
        return int(rng.choice(lower)), int(rng.choice(upper))

    if pattern == "left-right":
        left = nodes[cols <= 2]
        right = nodes[cols >= 3]
        if rng.random() < 0.5:
            return int(rng.choice(left)), int(rng.choice(right))
        return int(rng.choice(right)), int(rng.choice(left))

    raise ValueError(f"Unsupported traffic pattern: {pattern}")


def simulate_trial(config: TrialConfig, topology: Topology | None = None) -> TrialResult:
    topology = build_irregular_grid_topology() if topology is None else topology
    distances = shortest_path_distances(topology)
    shortest_policy = shortest_path_policy(
        topology,
        distances,
        tie_break_order=config.tie_break_order,
    )

    neighbors = _build_mutable_neighbors(topology, config.tie_break_order)
    rng = np.random.default_rng(config.seed)

    q_values: np.ndarray | None
    if config.mode == "shortest-path":
        q_values = None
    else:
        q_values = np.full(
            (topology.node_count, topology.node_count, topology.node_count),
            fill_value=np.inf,
            dtype=float,
        )
        for node in range(topology.node_count):
            for destination in range(topology.node_count):
                if node == destination:
                    continue
                for neighbor in neighbors[node]:
                    q_values[node, destination, neighbor] = config.initial_q_value
                    if neighbor == destination:
                        q_values[node, destination, neighbor] = 0.0

    packets: dict[int, list[int]] = {}
    queues = [deque() for _ in range(topology.node_count)]
    deliveries: list[tuple[int, int]] = []
    packet_id = 0
    active_packets = 0
    load_schedule = (
        ((0, config.load),) if config.load_schedule is None else config.load_schedule
    )
    event_index = 0
    sorted_events = tuple(sorted(config.topology_events, key=lambda item: item.at))

    for step in range(config.steps):
        while event_index < len(sorted_events) and sorted_events[event_index].at == step:
            _apply_topology_event(neighbors, sorted_events[event_index], topology, q_values)
            event_index += 1

        load = float(_scheduled_value(step, load_schedule))
        traffic_pattern = _scheduled_value(step, config.traffic_schedule)
        arrivals = int(rng.poisson(load))
        for _ in range(arrivals):
            if active_packets >= config.active_packet_limit:
                break
            source, destination = _sample_packet_pair(rng, traffic_pattern, topology)
            packets[packet_id] = [destination, step, step]
            queues[source].append(packet_id)
            packet_id += 1
            active_packets += 1

        incoming: list[tuple[int, int]] = []
        delivered_packet_ids: list[int] = []

        for node in range(topology.node_count):
            if not queues[node]:
                continue

            current_packet = queues[node].popleft()
            destination, created_at, enqueued_at = packets[current_packet]

            if config.mode == "shortest-path":
                next_hop = int(shortest_policy[node, destination])
            else:
                candidates = neighbors[node]
                if not candidates:
                    queues[node].appendleft(current_packet)
                    continue

                values = q_values[node, destination, candidates]
                next_hop = int(candidates[int(np.argmin(values))])
                wait_time = step - enqueued_at

                if config.mode == "q-routing":
                    future = 0.0
                    if next_hop != destination and neighbors[next_hop]:
                        future = float(np.min(q_values[next_hop, destination, neighbors[next_hop]]))
                    target = wait_time + config.transmission_time + future
                    q_values[node, destination, next_hop] += config.learning_rate * (
                        target - q_values[node, destination, next_hop]
                    )
                elif config.mode == "full-echo":
                    for neighbor in candidates:
                        future = 0.0
                        if neighbor != destination and neighbors[neighbor]:
                            future = float(
                                np.min(q_values[neighbor, destination, neighbors[neighbor]])
                            )
                        target = wait_time + config.transmission_time + future
                        q_values[node, destination, neighbor] += config.learning_rate * (
                            target - q_values[node, destination, neighbor]
                        )
                else:
                    raise ValueError(f"Unsupported mode: {config.mode}")

            if next_hop == destination:
                delivered_at = step + config.transmission_time
                deliveries.append((delivered_at, delivered_at - created_at))
                delivered_packet_ids.append(current_packet)
                active_packets -= 1
            else:
                packets[current_packet][2] = step + config.transmission_time
                incoming.append((next_hop, current_packet))

        for next_hop, current_packet in incoming:
            queues[next_hop].append(current_packet)
        for current_packet in delivered_packet_ids:
            del packets[current_packet]

    if config.mode == "shortest-path":
        policy = shortest_policy.copy()
    else:
        policy = np.full((topology.node_count, topology.node_count), fill_value=-1, dtype=int)
        for node in range(topology.node_count):
            for destination in range(topology.node_count):
                if node == destination or not neighbors[node]:
                    continue
                candidates = neighbors[node]
                values = q_values[node, destination, candidates]
                policy[node, destination] = int(candidates[int(np.argmin(values))])

    return TrialResult(
        config=config,
        topology=topology,
        deliveries=np.asarray(deliveries, dtype=int),
        q_values=q_values,
        policy=policy,
        shortest_path_policy=shortest_policy,
        distances=distances,
    )


def load_sweep(
    *,
    mode: Mode,
    load_levels: list[float] | None = None,
    trial_count: int = 19,
    steps: int = DEFAULT_STEPS,
    settle_time: int = DEFAULT_SETTLE_TIME,
    learning_rate: float = 0.5,
) -> dict[str, object]:
    load_levels = load_levels or [0.5 + 0.5 * index for index in range(9)]
    trials_by_load: dict[float, list[float]] = {}
    for load in load_levels:
        trial_means = []
        for seed in range(trial_count):
            result = simulate_trial(
                TrialConfig(
                    mode=mode,
                    load=load,
                    steps=steps,
                    settle_time=settle_time,
                    learning_rate=learning_rate,
                    seed=seed,
                )
            )
            trial_means.append(result.mean_delivery_time())
        trials_by_load[load] = trial_means

    medians = {
        load: float(statistics.median(values)) for load, values in trials_by_load.items()
    }
    return {
        "mode": mode,
        "load_levels": load_levels,
        "trial_count": trial_count,
        "trial_means": trials_by_load,
        "medians": medians,
    }


def figure2_trials() -> dict[str, TrialResult]:
    return {
        "q_low": simulate_trial(
            TrialConfig(mode="q-routing", load=FIGURE2_LOW_LOAD, seed=0)
        ),
        "sp_low": simulate_trial(
            TrialConfig(mode="shortest-path", load=FIGURE2_LOW_LOAD, seed=0)
        ),
        "q_high": simulate_trial(
            TrialConfig(mode="q-routing", load=FIGURE2_HIGH_LOAD, seed=0)
        ),
        "sp_high": simulate_trial(
            TrialConfig(mode="shortest-path", load=FIGURE2_HIGH_LOAD, seed=0)
        ),
    }


def dynamic_scenarios() -> dict[str, TrialResult]:
    topology = build_irregular_grid_topology()
    bridge = (2 * 6 + 2, 2 * 6 + 3)
    return {
        "topology_change": simulate_trial(
            TrialConfig(
                mode="q-routing",
                load=2.0,
                seed=1,
                topology_events=(TopologyEvent(at=5_000, remove_edges=(bridge,)),),
            ),
            topology=topology,
        ),
        "traffic_change": simulate_trial(
            TrialConfig(
                mode="q-routing",
                load=2.0,
                seed=2,
                traffic_schedule=((0, "upper-lower"), (5_000, "left-right")),
            ),
            topology=topology,
        ),
        "load_change": simulate_trial(
            TrialConfig(
                mode="q-routing",
                load=1.0,
                seed=3,
                load_schedule=((0, 1.0), (3_000, 2.5), (6_000, 1.0)),
            ),
            topology=topology,
        ),
    }


def plot_topology(ax, topology: Topology) -> None:
    import matplotlib.pyplot as plt

    for left, right in topology.edges:
        left_row, left_col = topology.coordinates[left]
        right_row, right_col = topology.coordinates[right]
        ax.plot([left_col, right_col], [-left_row, -right_row], color="black", linewidth=1.2)
    rows = [topology.coordinates[node][0] for node in range(topology.node_count)]
    cols = [topology.coordinates[node][1] for node in range(topology.node_count)]
    ax.scatter(cols, [-row for row in rows], color="black", s=36, zorder=3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Irregular 6x6 grid topology")
    plt.tight_layout()


def plot_policy_summary(ax, topology: Topology, counts: np.ndarray, title: str) -> None:
    for left, right in topology.edges:
        left_row, left_col = topology.coordinates[left]
        right_row, right_col = topology.coordinates[right]
        ax.plot([left_col, right_col], [-left_row, -right_row], color="#999999", linewidth=1.0)

    for node in range(topology.node_count):
        row, col = topology.coordinates[node]
        ax.text(
            col,
            -row,
            str(int(counts[node])),
            ha="center",
            va="center",
            fontsize=8,
            fontfamily="monospace",
        )

    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)


def plot_delivery_curve(ax, result_a: TrialResult, result_b: TrialResult, title: str) -> None:
    curve_a_x, curve_a_y = result_a.binned_delivery_curve()
    curve_b_x, curve_b_y = result_b.binned_delivery_curve()
    ax.plot(curve_a_x, curve_a_y, label=result_a.config.mode, linewidth=1.5)
    ax.plot(curve_b_x, curve_b_y, label=result_b.config.mode, linestyle="--", linewidth=1.5)
    ax.set_title(title)
    ax.set_xlabel("Simulator time")
    ax.set_ylabel("Average delivery time")
    ax.legend()


def plot_load_sweep(ax, sweep_data: list[dict[str, object]], title: str) -> None:
    for data in sweep_data:
        load_levels = data["load_levels"]
        medians = data["medians"]
        y_values = [medians[load] for load in load_levels]
        label = str(data["mode"])
        linestyle = "--" if label == "shortest-path" else ":"
        if label == "q-routing":
            linestyle = "-"
        ax.plot(load_levels, y_values, label=label, linestyle=linestyle, linewidth=1.6)
    ax.set_title(title)
    ax.set_xlabel("Network load level")
    ax.set_ylabel("Average delivery time")
    ax.legend()


def paper_summary_error(counts_grid: np.ndarray, paper_grid: np.ndarray) -> int:
    return int(np.abs(counts_grid - paper_grid).sum())


def _smoke_test() -> None:
    topology = build_irregular_grid_topology()
    distances = shortest_path_distances(topology)
    shortest = shortest_path_policy(topology, distances)
    counts = topology.to_grid(
        policy_route_counts(shortest, include_source=True, include_destination=False)
    )
    print("topology_nodes", topology.node_count)
    print("topology_edges", len(topology.edges))
    print(
        "shortest_path_summary_l1_error",
        paper_summary_error(counts, PAPER_POLICY_SUMMARY_SHORTEST),
    )
    q_result = simulate_trial(TrialConfig(mode="q-routing", load=2.5, seed=0))
    sp_result = simulate_trial(TrialConfig(mode="shortest-path", load=2.5, seed=0))
    print("q_mean_after_settle", round(q_result.mean_delivery_time(), 3))
    print("sp_mean_after_settle", round(sp_result.mean_delivery_time(), 3))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a small end-to-end smoke test and print summary metrics.",
    )
    args = parser.parse_args()

    if args.smoke_test:
        _smoke_test()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
'''


def md(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(textwrap.dedent(source).strip() + "\n")


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(textwrap.dedent(source).strip() + "\n")


def inline_repro_code() -> str:
    source = textwrap.dedent(REPRO_SOURCE).strip()
    if "\n\ndef main() -> None:\n" in source:
        source = source.split("\n\ndef main() -> None:\n", 1)[0].rstrip()

    return (
        f"{source}\n\n"
        "import matplotlib.pyplot as plt\n"
        'plt.style.use("seaborn-v0_8-whitegrid")\n'
        "np.set_printoptions(linewidth=120)\n"
    )


def build_notebook() -> nbf.NotebookNode:
    notebook = nbf.v4.new_notebook()
    notebook["cells"] = [
        md(
            """
            # Packet Routing in Dynamically Changing Networks: A Reinforcement Learning Approach

            Justin A. Boyan and Michael L. Littman, NeurIPS 1993

            This notebook implements a reproduction of the paper.
            It covers Q-routing, shortest-path routing, and full-echo Q-routing, and recreates
            Figures 2-5 together with the dynamic-change scenarios discussed in Section 3.1.
            """
        ),
        md(
            """
            ## Reproduction Strategy and Explicit Assumptions

            The paper text does not fully specify the following details.

            - The exact definition of `network load level`
            - The tie-break rule for the shortest-path baseline
            - The exact low-load and high-load values used in Figure 2
            - The exact rule behind `after learning has settled` in Figures 4 and 5
            - The concrete schedules for topology, traffic, and load changes in Section 3.1

            This notebook uses the following reproducible assumptions.

            1. A load level is interpreted as the mean number of packet arrivals per tick, implemented with Poisson arrivals.
            2. The active packet limit is set to `1000`, matching the technical report CMU-CS-93-165 referenced by the paper.
            3. The transmission time `s` is set to 1 tick.
            4. The default learning rate is `0.5`, following the conference paper, while the `0.7` value in the technical report is noted explicitly as a source discrepancy.
            5. Because the shortest-path tie-break rule is not stated, this reproduction uses the simple directional priority `W > E > N > S`, which minimizes the mismatch with the left panel of Figure 3.
            6. `After learning has settled` is approximated here by averaging packet latencies for packets delivered at `t >= 5000`.
            7. The dynamic scenarios in Section 3.1 are reproduced qualitatively with explicit representative change points documented in the notebook.

            As a result, this notebook reproduces the main quantitative and qualitative evaluations
            from the paper, but the final numbers still depend on the assumptions above wherever
            the original text is underspecified.
            """
        ),
        md(
            """
            ## Self-Contained Implementation

            The full simulation and plotting code is included in this notebook on purpose.
            The notebook does not depend on repo-local Python modules at execution time.
            """
        ),
        code(inline_repro_code()),
        md(
            """
            ## Figure 1: Reconstructed Irregular 6x6 Grid

            The topology below is reconstructed directly from Figure 1 in the paper.
            """
        ),
        code(
            """
            topology = build_irregular_grid_topology()

            fig, ax = plt.subplots(figsize=(6, 5))
            plot_topology(ax, topology)
            plt.show()
            """
        ),
        md(
            """
            ## Shortest-Path Baseline Sanity Check

            The shortest-path tie-break rule is not specified in the paper.
            This reproduction therefore uses a simple deterministic rule chosen to stay close to
            the left policy-summary panel in Figure 3. The cell below compares the reproduced
            summary against the one printed in the paper.
            """
        ),
        code(
            """
            distances = shortest_path_distances(topology)
            sp_policy = shortest_path_policy(topology, distances)
            sp_counts = policy_route_counts(
                sp_policy,
                include_source=True,
                include_destination=False,
            )
            sp_grid = topology.to_grid(sp_counts)

            print("Reproduced shortest-path summary:")
            print(sp_grid)
            print()
            print("Paper shortest-path summary:")
            print(PAPER_POLICY_SUMMARY_SHORTEST)
            print()
            print("L1 error:", paper_summary_error(sp_grid, PAPER_POLICY_SUMMARY_SHORTEST))

            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            plot_policy_summary(axes[0], topology, sp_counts, "Reproduced shortest-path summary")
            plot_policy_summary(
                axes[1],
                topology,
                PAPER_POLICY_SUMMARY_SHORTEST.reshape(-1),
                "Paper shortest-path summary",
            )
            plt.tight_layout()
            plt.show()
            """
        ),
        md(
            """
            ## Figure 2: Time Evolution Under Low and High Load

            The paper does not provide the exact low-load and high-load values used for Figure 2.
            This reproduction uses the common convention `low = 1.0` and `high = 2.5`.
            """
        ),
        code(
            """
            figure2 = figure2_trials()

            fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
            plot_delivery_curve(
                axes[0],
                figure2["q_low"],
                figure2["sp_low"],
                f"Low load (assumed load={FIGURE2_LOW_LOAD})",
            )
            plot_delivery_curve(
                axes[1],
                figure2["q_high"],
                figure2["sp_high"],
                f"High load (assumed load={FIGURE2_HIGH_LOAD})",
            )
            plt.tight_layout()
            plt.show()

            print("Low-load mean delivery times after settle:")
            print("  q-routing     :", round(figure2["q_low"].mean_delivery_time(), 3))
            print("  shortest-path :", round(figure2["sp_low"].mean_delivery_time(), 3))
            print()
            print("High-load mean delivery times after settle:")
            print("  q-routing     :", round(figure2["q_high"].mean_delivery_time(), 3))
            print("  shortest-path :", round(figure2["sp_high"].mean_delivery_time(), 3))
            """
        ),
        md(
            """
            ## Figure 3: Policy Summary Under High Load

            The Q-routing policy summary in the paper comes from a representative single run.
            This reproduction follows the same pattern by fixing a seed and visualizing one run explicitly.
            """
        ),
        code(
            """
            representative_q = simulate_trial(
                TrialConfig(mode="q-routing", load=FIGURE2_HIGH_LOAD, seed=2)
            )
            representative_q_counts = representative_q.policy_counts(
                include_source=True,
                include_destination=False,
            )
            representative_q_grid = topology.to_grid(representative_q_counts)

            print("Reproduced Q-routing summary (seed=2):")
            print(representative_q_grid)
            print()
            print("Paper Q-routing summary:")
            print(PAPER_POLICY_SUMMARY_Q_ROUTING)
            print()
            print("L1 error:", paper_summary_error(representative_q_grid, PAPER_POLICY_SUMMARY_Q_ROUTING))

            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            plot_policy_summary(
                axes[0],
                topology,
                representative_q_counts,
                "Reproduced Q-routing summary (seed=2)",
            )
            plot_policy_summary(
                axes[1],
                topology,
                PAPER_POLICY_SUMMARY_Q_ROUTING.reshape(-1),
                "Paper Q-routing summary",
            )
            plt.tight_layout()
            plt.show()
            """
        ),
        md(
            """
            ## Figure 4: Q-routing vs shortest paths

            Following the paper, this sweep uses load levels `0.5 ... 4.5` and reports the median
            over 19 trials. This is the heaviest cell in the notebook and may take several minutes
            to finish when the notebook is executed end-to-end.
            """
        ),
        code(
            """
            figure4_q = load_sweep(mode="q-routing", trial_count=19)
            figure4_sp = load_sweep(mode="shortest-path", trial_count=19)

            fig, ax = plt.subplots(figsize=(8, 5))
            plot_load_sweep(ax, [figure4_q, figure4_sp], "Figure 4 reproduction")
            plt.tight_layout()
            plt.show()

            print("Figure 4 medians:")
            for load in figure4_q["load_levels"]:
                print(
                    f"load={load:>3}: "
                    f"q-routing={figure4_q['medians'][load]:>8.3f}, "
                    f"shortest-path={figure4_sp['medians'][load]:>8.3f}"
                )
            """
        ),
        md(
            """
            ## Figure 5: Comparison Including Full-Echo Q-Routing

            The paper states only that full-echo Q-routing adjusts `Qx(d, y)` using estimates
            returned by each neighbor. In this reproduction, that is implemented by applying
            `q + s + min_z Q_y(d, z)` to every neighbor-specific estimate. Like Figure 4, this
            full sweep is expensive and may take several minutes to complete.
            """
        ),
        code(
            """
            figure5_full_echo = load_sweep(mode="full-echo", trial_count=19)

            fig, ax = plt.subplots(figsize=(8, 5))
            plot_load_sweep(
                ax,
                [figure4_q, figure4_sp, figure5_full_echo],
                "Figure 5 reproduction",
            )
            plt.tight_layout()
            plt.show()

            print("Figure 5 medians:")
            for load in figure4_q["load_levels"]:
                print(
                    f"load={load:>3}: "
                    f"q-routing={figure4_q['medians'][load]:>8.3f}, "
                    f"shortest-path={figure4_sp['medians'][load]:>8.3f}, "
                    f"full-echo={figure5_full_echo['medians'][load]:>8.3f}"
                )
            """
        ),
        md(
            """
            ## Section 3.1: dynamically changing networks

            The paper describes these experiments only qualitatively, so this notebook fixes one
            representative schedule for each type of change while preserving the intended behavior.

            - topology change: remove one central bridge at `t=5000`
            - traffic pattern change: switch from `upper-lower` to `left-right`
            - load change: `1.0 -> 2.5 -> 1.0`
            """
        ),
        code(
            """
            scenarios = dynamic_scenarios()

            fig, axes = plt.subplots(1, 3, figsize=(18, 4), sharey=True)
            for ax, (name, result), markers in zip(
                axes,
                scenarios.items(),
                ([5000], [5000], [3000, 6000]),
            ):
                x, y = result.binned_delivery_curve(bin_size=100)
                ax.plot(x, y, linewidth=1.5)
                for marker in markers:
                    ax.axvline(marker, color="black", linestyle="--", linewidth=1.0)
                ax.set_title(name.replace("_", " "))
                ax.set_xlabel("Simulator time")
            axes[0].set_ylabel("Average delivery time")
            plt.tight_layout()
            plt.show()

            for name, result in scenarios.items():
                print(name, "mean after settle:", round(result.mean_delivery_time(), 3))
            """
        ),
        md(
            """
            ## Summary

            This notebook provides an executable reproduction of the paper's core evaluation.

            - Figures 1-5 can be regenerated directly from code
            - The dynamic scenarios in Section 3.1 are reproduced qualitatively
            - Underspecified parts of the paper are surfaced explicitly as notebook assumptions

            The main sources of mismatch with the paper are the parts the paper leaves unspecified.

            - The exact definition of load level
            - shortest-path tie-break
            - The exact settling criterion
            - The concrete dynamic-change schedule
            - The exact operational details of the full-echo update
            """
        ),
    ]
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12",
        },
    }
    return notebook


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook()
    OUTPUT.write_text(nbf.writes(notebook), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
