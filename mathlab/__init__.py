"""ProofWeave: auditable mathematics research infrastructure."""

from .fact_graph import FactGraph
from .issue_ledger import IssueLedger
from .source_registry import SourceRegistry

__all__ = ["FactGraph", "IssueLedger", "SourceRegistry"]
__version__ = "0.1.0"
