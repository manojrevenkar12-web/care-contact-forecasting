import pytest

from ccf.config import WAREHOUSE


@pytest.fixture(scope="session")
def store():
    """The world and the warehouse, built once for the test session if they are missing."""
    if not WAREHOUSE.exists():
        from ccf.etl.run import run
        from ccf.world.generate import build

        build()
        run()
    from ccf.data import load

    return load()
