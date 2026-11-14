"""In-memory fakes for every seam in `receipts.contracts`. Unit tests never touch the network.

Frozen after Wave 0: a lane that needs more fake behaviour builds it in its own tests.
"""

from receipts.fakes.keenable import FakeKeenable
from receipts.fakes.llm import fake_llm
from receipts.fakes.repo import InMemoryRunRepo
from receipts.fakes.service import FakeRunService

__all__ = ["FakeKeenable", "FakeRunService", "InMemoryRunRepo", "fake_llm"]
