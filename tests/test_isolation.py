"""Nothing that forecasts, staffs or analyses reads the truth; only the backtest does."""

from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ccf"


def test_only_the_backtest_reads_the_truth():
    for f in SRC.rglob("*.py"):
        rel = f.relative_to(SRC).as_posix()
        if rel.startswith(("evals/", "world/")) or rel == "config.py":
            continue
        text = f.read_text()
        assert "TRUTH" not in text and "truth.json" not in text, rel


def test_the_held_out_setup_is_as_pinned():
    import hashlib

    from ccf.config import CONFIG

    lock = (CONFIG / "heldout.lock").read_text().split()
    world = hashlib.sha256((CONFIG / "world.toml").read_bytes()).hexdigest()
    from ccf.evals.backtest import origins

    held = hashlib.sha256(",".join(origins("heldout")).encode()).hexdigest()
    assert lock[0] == world and lock[1] == held
