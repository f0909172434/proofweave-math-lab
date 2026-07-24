class MathLabError(Exception):
    """Base error for expected, user-actionable ProofWeave failures."""


class ValidationError(MathLabError):
    """An artifact failed a deterministic validation gate."""


class IntegrityError(MathLabError):
    """A truth-layer or append-only invariant would be violated."""


class RoutingError(MathLabError):
    """No safe routing decision can be executed."""


class ConfigurationRequired(MathLabError):
    """A disabled capability requires explicit user configuration."""
