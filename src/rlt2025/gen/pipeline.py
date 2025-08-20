"""Pipeline orchestration for procedural generation stages."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .context import GenContext
from .edits import Edits
from .stage import Stage

if TYPE_CHECKING:
    pass


@dataclass
class Pipeline:
    """
    Orchestrates a sequence of generation stages with dependency validation.

    The pipeline:
    - Validates that all stage dependencies are satisfied
    - Runs stages in the order provided
    - Commits edits after each stage (can be batched if needed)
    - Tracks what has been provided for dependency checking
    """

    stages: list[Stage] = field(default_factory=list)
    batch_commits: bool = False  # If True, commit all edits at end instead of per-stage

    def add_stage(self, stage: Stage) -> None:
        """Add a stage to the pipeline."""
        self.stages.append(stage)

    def validate_dependencies(self) -> None:
        """
        Validate that all stage dependencies can be satisfied.

        Raises RuntimeError if any stage has unsatisfied dependencies.
        """
        satisfied: set[str] = set()

        for stage in self.stages:
            missing = stage.requires - satisfied
            if missing:
                raise RuntimeError(
                    f"Stage '{stage.id}' requires {missing} but only {satisfied} "
                    f"are provided by previous stages"
                )
            satisfied |= stage.provides

    def run(self, ctx: GenContext) -> None:
        """
        Run the complete pipeline on the given generation context.

        This validates dependencies, then runs each stage in sequence,
        committing edits either after each stage or at the end.
        """
        self.validate_dependencies()

        if self.batch_commits:
            all_edits = Edits()

        satisfied: set[str] = set()

        for stage in self.stages:
            # Dependencies already validated in validate_dependencies(),
            # no need to double-check at runtime

            # Run the stage
            edits = stage.apply(ctx)

            # Commit or batch the edits
            if self.batch_commits:
                all_edits.merge(edits)
            else:
                ctx.procgen.commit(edits)

            # Track what's now available
            satisfied |= stage.provides

        # Commit all batched edits at once
        if self.batch_commits:
            ctx.procgen.commit(all_edits)

    def get_stage_order(self) -> list[str]:
        """Get the list of stage IDs in execution order."""
        return [stage.id for stage in self.stages]

    def get_all_provides(self) -> set[str]:
        """Get the set of all things this pipeline provides."""
        provides = set()
        for stage in self.stages:
            provides |= stage.provides
        return provides

    def get_all_requires(self) -> set[str]:
        """Get the set of all external requirements for this pipeline."""
        provides = set()
        requires = set()

        for stage in self.stages:
            requires |= stage.requires - provides
            provides |= stage.provides

        return requires
