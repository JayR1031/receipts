"""Lane L1: pack loader, SpecialistRunner, Coordinator, InProcessRunService. Owned by L1 from W1.

W2 wiring: `InProcessRunService(Coordinator(packs, SpecialistRunner(search, fetch,
verify=receipts.verify.verify_claim, repair_factory=live_repair_factory),
max_concurrent=settings.max_concurrent_specialists), repo)`. Repairs: `receipts.harness.repair`.
"""

from receipts.harness.coordinator import Coordinator, Specialist
from receipts.harness.live import KeenableFetchClient, KeenableSearchClient, live_model_factory
from receipts.harness.packs import load_pack
from receipts.harness.repair import (
    MAX_REPAIRS,
    ClaimRepairer,
    MelleaClaimRepairer,
    RepairFactory,
    RepairRequest,
)
from receipts.harness.service import InProcessRunService, new_uuid_run_id
from receipts.harness.specialist import (
    Clock,
    ModelFactory,
    SpecialistRunner,
    Verify,
    default_model_factory,
    parse_claims,
    passthrough_verify,
    utc_now,
)
from receipts.harness.tools import ToolLog, make_tools

__all__ = [
    "MAX_REPAIRS",
    "ClaimRepairer",
    "Clock",
    "Coordinator",
    "InProcessRunService",
    "KeenableFetchClient",
    "KeenableSearchClient",
    "MelleaClaimRepairer",
    "ModelFactory",
    "RepairFactory",
    "RepairRequest",
    "Specialist",
    "SpecialistRunner",
    "ToolLog",
    "Verify",
    "default_model_factory",
    "live_model_factory",
    "load_pack",
    "make_tools",
    "new_uuid_run_id",
    "parse_claims",
    "passthrough_verify",
    "utc_now",
]
