import numpy as np
import tcod
from rlt2025.components import Position, VisibilityInfo
from rlt2025.ecs import World
from rlt2025.events import EntityMovedEvent, BeforeFrameRenderEvent


class VisibilitySystem:
    def __init__(self, world: World):
        world.event_bus.register(EntityMovedEvent, self.dirty_visibility)
        world.event_bus.register(BeforeFrameRenderEvent, self.update_visibility)

    def dirty_visibility(self, event: EntityMovedEvent, world: World) -> None:
        entity = event.entity
        vis = world.entities.get_component(entity, VisibilityInfo)
        if vis is not None:
            vis.dirty = True

    def update_visibility(self, event: BeforeFrameRenderEvent, world: World) -> None:
        for entity, pos, vis in world.entities.query(Position, VisibilityInfo):
            if vis.dirty:
                vis.dirty = False

                if (
                    vis.visible is None
                    or vis.visible.shape != world.game_map.tiles["transparent"].shape
                ):
                    vis.visible = np.full_like(
                        world.game_map.tiles["transparent"],
                        False,
                        dtype=bool,
                    )

                vis.visible = tcod.map.compute_fov(
                    transparency=world.game_map.tiles["transparent"],
                    pov=(pos.x, pos.y),
                    radius=vis.sight_radius,
                )
                if vis.compute_explored:
                    if (
                        vis.explored is None
                        or vis.explored.shape
                        != world.game_map.tiles["transparent"].shape
                    ):
                        vis.explored = np.full_like(
                            world.game_map.tiles["transparent"],
                            False,
                            dtype=bool,
                        )
                    vis.explored = vis.explored | vis.visible
                else:
                    vis.explored = None
