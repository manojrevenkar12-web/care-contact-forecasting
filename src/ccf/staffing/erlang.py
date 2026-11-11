"""Erlang C, vectorised: how many agents an interval needs for a service level, and the service level a given
number of agents achieves on the volume that really arrived."""

from __future__ import annotations

import numpy as np


def _walk(load: np.ndarray, n_max: int):
    """Yield (n, Erlang C probability of waiting) for n = 1..n_max, for every interval at once."""
    b = np.ones_like(load)
    for n in range(1, n_max + 1):
        b = load * b / (n + load * b)
        with np.errstate(divide="ignore", invalid="ignore"):
            c = np.where(n > load, n * b / (n - load * (1 - b)), 1.0)
        yield n, np.clip(c, 0, 1)


def service_level(agents: np.ndarray, load: np.ndarray, aht: float, within: float) -> np.ndarray:
    """Share answered within `within` seconds with `agents` agents and `load` Erlangs offered."""
    agents = np.maximum(agents.astype(int), 0)
    out = np.where(load <= 0, 1.0, 0.0)
    for n, c in _walk(load, int(agents.max(initial=0))):
        sel = (agents == n) & (load > 0)
        sl = np.where(n > load, 1 - c * np.exp(-(n - load) * within / aht), 0.0)
        out = np.where(sel, sl, out)
    return out


def required_agents(load: np.ndarray, aht: float, within: float, target: float, n_max: int = 600) -> np.ndarray:
    """The fewest agents that reach `target` service level; at least one while the line is open."""
    need = np.zeros(load.shape, dtype=int)
    open_ = np.ones(load.shape, dtype=bool)
    for n, c in _walk(load, n_max):
        sl = np.where(n > load, 1 - c * np.exp(-(n - load) * within / aht), 0.0)
        hit = open_ & ((sl >= target) | (load <= 0))
        need[hit] = n
        open_ &= ~hit
        if not open_.any():
            break
    need[open_] = n_max
    return need


def offered_load(volume: np.ndarray, aht: float, interval_seconds: float, concurrency: float = 1.0) -> np.ndarray:
    return volume * (aht / concurrency) / interval_seconds
