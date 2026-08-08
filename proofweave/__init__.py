"""ProofWeave Core v2 public API."""

from .pipeline import check_project, initialize, run_proof, status

__all__ = ["check_project", "initialize", "run_proof", "status"]
__version__ = "2.0.0"
