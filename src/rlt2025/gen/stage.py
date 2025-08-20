"""Stage interface and protocol for procedural generation."""

from typing import Protocol

from .context import GenContext
from .edits import Edits


class Stage(Protocol):
    """
    Protocol for procedural generation stages.

    Each stage:
    - Has a unique identifier
    - Declares what it provides to other stages
    - Declares what it requires from previous stages
    - Transforms a generation context into pure data edits
    """

    id: str
    provides: set[str]  # What this stage adds to the world/blackboard
    requires: set[str]  # What this stage needs from previous stages

    def apply(self, ctx: GenContext) -> Edits:
        """
        Apply this stage to the generation context.

        This should be a pure function that:
        - Reads from ctx.world, ctx.area, ctx.blackboard
        - Uses ctx.rng(namespace) for deterministic randomness
        - May write to ctx.blackboard for later stages
        - Returns Edits that describe what to change
        """
        ...
