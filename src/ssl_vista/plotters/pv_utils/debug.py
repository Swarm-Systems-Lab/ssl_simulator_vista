__all__ = [
    "inspect_actor",
]

import contextlib

import pyvista as pv


def inspect_actor(actor):
    # bounds, position, orientation
    # property (color/opacity)
    actor.GetProperty()
    with contextlib.suppress(Exception):
        pass

    # mapper + input dataset
    mapper = actor.GetMapper()
    if mapper is None:
        return

    dataset = mapper.GetInput()  # often a vtkPolyData
    if dataset is None:
        return

    # geometry counts
    with contextlib.suppress(Exception):
        pass

    # point-data arrays
    pd = dataset.GetPointData()
    if pd is not None:
        n = pd.GetNumberOfArrays()
        for i in range(n):
            pd.GetArrayName(i)
    # cell-data arrays
    cd = dataset.GetCellData()
    if cd is not None:
        n = cd.GetNumberOfArrays()
        for i in range(n):
            cd.GetArrayName(i)
