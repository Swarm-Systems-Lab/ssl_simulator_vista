import pyvista as pv

def inspect_actor(actor):
    # bounds, position, orientation
    print("Bounds:", actor.GetBounds())
    print("Position:", actor.GetPosition())
    print("Orientation:", actor.GetOrientation())
    print("Scale:", actor.GetScale())
    print("Visibility:", bool(actor.GetVisibility()))
    print("Pickable:", bool(actor.GetPickable()))
    # property (color/opacity)
    prop = actor.GetProperty()
    try:
        print("Color:", prop.GetColor())
        print("Opacity:", prop.GetOpacity())
    except Exception:
        pass

    # mapper + input dataset
    mapper = actor.GetMapper()
    if mapper is None:
        print("No mapper attached")
        return

    dataset = mapper.GetInput()  # often a vtkPolyData
    if dataset is None:
        print("Mapper has no input")
        return

    # geometry counts
    try:
        print("Num points:", dataset.GetNumberOfPoints())
        print("Num cells:", dataset.GetNumberOfCells())
    except Exception:
        pass

    # point-data arrays
    pd = dataset.GetPointData()
    if pd is not None:
        n = pd.GetNumberOfArrays()
        print("PointData arrays:", n)
        for i in range(n):
            name = pd.GetArrayName(i)
            print(" - point array", i, name)
    # cell-data arrays
    cd = dataset.GetCellData()
    if cd is not None:
        n = cd.GetNumberOfArrays()
        print("CellData arrays:", n)
        for i in range(n):
            name = cd.GetArrayName(i)
            print(" - cell array", i, name)