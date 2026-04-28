__all__ = [
    "inspect_actor",
]

import contextlib
import logging

_logger = logging.getLogger(__name__)


def _actor_snapshot(actor) -> dict:
    """Build a structured snapshot of a VTK actor. No logging side effects."""
    snap = {
        "bounds": actor.GetBounds(),
        "position": actor.GetPosition(),
        "orientation": actor.GetOrientation(),
        "scale": actor.GetScale(),
        "visible": bool(actor.GetVisibility()),
        "pickable": bool(actor.GetPickable()),
    }

    prop = actor.GetProperty()
    if prop is not None:
        with contextlib.suppress(Exception):
            snap["property"] = {
                "color": prop.GetColor(),
                "opacity": prop.GetOpacity(),
            }

    mapper = actor.GetMapper()
    if mapper is None:
        snap["mapper"] = None
        return snap

    dataset = mapper.GetInput()
    if dataset is None:
        snap["mapper"] = {"input": None}
        return snap

    mapper_info = {}
    with contextlib.suppress(Exception):
        mapper_info["num_points"] = dataset.GetNumberOfPoints()
        mapper_info["num_cells"] = dataset.GetNumberOfCells()

    pd = dataset.GetPointData()
    if pd is not None:
        mapper_info["point_arrays"] = [pd.GetArrayName(i) for i in range(pd.GetNumberOfArrays())]

    cd = dataset.GetCellData()
    if cd is not None:
        mapper_info["cell_arrays"] = [cd.GetArrayName(i) for i in range(cd.GetNumberOfArrays())]

    snap["mapper"] = mapper_info
    return snap


def inspect_actor(actor, name: str | None = None) -> None:
    """Log a structured snapshot of a VTK actor at DEBUG level."""
    if not _logger.isEnabledFor(logging.DEBUG):
        return  # skip the snapshot work entirely
    snap = _actor_snapshot(actor)
    msg = f"actor inspection: {name}" if name else "actor inspection"
    _logger.debug(msg, extra={"actor": snap})
