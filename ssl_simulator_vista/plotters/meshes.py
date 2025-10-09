import numpy as np
import pyvista as pv

from ssl_simulator.math import unit_vec

def create_sphere_grid(radius=1.0, lat_step=15, lon_step=15,  lon_angles=None, resolution=360//4):
    """
    Fast creation of a sphere wireframe grid with only latitude and longitude lines.
    Returns a single PolyData mesh.
    """
    points = []
    lines = []

    # --- Latitude circles ---
    if lat_step is not None:
        for phi_deg in range(-90 + lat_step, 90, lat_step):
            phi = np.deg2rad(phi_deg)
            theta_vals = np.linspace(0, 2*np.pi, resolution)
            x = radius * np.cos(phi) * np.cos(theta_vals)
            y = radius * np.cos(phi) * np.sin(theta_vals)
            z = radius * np.sin(phi) * np.ones_like(theta_vals)
            start_idx = len(points)
            points.extend(np.c_[x, y, z])
            # create line connectivity
            for i in range(len(theta_vals) - 1):
                lines.append([2, start_idx + i, start_idx + i + 1])
            # close the circle
            lines.append([2, start_idx + len(theta_vals) - 1, start_idx])

    # --- Longitude circles ---
    if lon_step is not None:
        if lon_angles is None:
            lon_angles = np.arange(0, 360, lon_step)
        for theta_deg in lon_angles:
            theta = np.deg2rad(theta_deg)   
            phi_vals = np.linspace(-np.pi/2, np.pi/2, resolution)
            x = radius * np.cos(phi_vals) * np.cos(theta)
            y = radius * np.cos(phi_vals) * np.sin(theta)
            z = radius * np.sin(phi_vals)
            start_idx = len(points)
            points.extend(np.c_[x, y, z])
            for i in range(len(phi_vals) - 1):
                lines.append([2, start_idx + i, start_idx + i + 1])

    points = np.array(points)
    lines = np.array(lines, dtype=np.int64).flatten()
    grid_mesh = pv.PolyData()
    grid_mesh.points = points
    grid_mesh.lines = lines
    return grid_mesh

def latlon_to_xyz(lat_deg, lon_deg, radius=1.0):
    """
    Convert latitude and longitude in degrees to 3D Cartesian coordinates on a sphere.
    Latitude: -90 (south pole) to 90 (north pole)
    Longitude: 0-360, 0 = prime meridian
    """
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)
    x = radius * np.cos(lat) * np.cos(lon)
    y = radius * np.cos(lat) * np.sin(lon)
    z = radius * np.sin(lat)
    return np.array([x, y, z])


def create_geodesic(latlon_start, latlon_end, radius=1.0, n_points=100):
    """
    Create a PolyData line along the geodesic between two lat/lon points on a sphere.
    
    Parameters:
    - latlon_start: (lat_deg, lon_deg)
    - latlon_end: (lat_deg, lon_deg)
    - radius: sphere radius
    - n_points: number of points along the geodesic
    """
    # Convert to Cartesian
    start = latlon_to_xyz(*latlon_start, radius)
    end = latlon_to_xyz(*latlon_end, radius)

    # Normalize vectors
    start_unit = unit_vec(start)
    end_unit = unit_vec(end)

    # Compute angle between vectors
    dot = np.clip(np.dot(start_unit, end_unit), -1.0, 1.0)
    omega = np.arccos(dot)

    # Check for numerical issues
    eps = 1e-10
    if np.isclose(omega, 0, atol=eps):
        raise ValueError(f"Numerical problem: start {latlon_start} and end {latlon_end} points are coincident (omega = {np.round(omega, 6)}).")
    if np.isclose(omega, np.pi, atol=eps):
        raise ValueError(f"Numerical problem: start {latlon_start} and end {latlon_end} points are nearly antipodal (omega = {np.round(omega, 6)}).")

    # Slerp interpolation along the great circle
    t = np.linspace(0, 1, n_points)
    points = (np.sin((1 - t) * omega)[:, None] * start_unit + np.sin(t * omega)[:, None] * end_unit) / np.sin(omega)
    points *= radius

    # Create PolyData line
    line = pv.PolyData()
    line.points = points

    # Line connectivity
    n_pts = len(points)
    lines = np.empty((n_pts - 1, 3), dtype=np.int64)
    lines[:, 0] = 2  # two points per segment
    lines[:, 1] = np.arange(n_pts - 1)
    lines[:, 2] = np.arange(1, n_pts)
    line.lines = lines.flatten()
    return line

def make_dashed_line(polyline, dash_length=5):
    """
    polyline: pv.PolyData with a line
    dash_length: number of points per dash
    """
    points = polyline.points
    n = len(points)
    new_lines = []
    new_points = []

    for i in range(0, n - 1, dash_length*2):
        start_idx = len(new_points)
        segment_points = points[i:i+dash_length]
        if len(segment_points) < 2:
            continue
        new_points.extend(segment_points)
        seg_len = len(segment_points)
        for j in range(seg_len - 1):
            new_lines.append([2, start_idx + j, start_idx + j + 1])

    dashed = pv.PolyData()
    dashed.points = np.array(new_points)
    dashed.lines = np.array(new_lines, dtype=np.int64).flatten()
    return dashed

if __name__ == "__main__":

    mesh1 = create_sphere_grid(radius=1.0, lat_step=15, lon_step=15)
    mesh2 = create_sphere_grid(radius=1.0, lat_step=90, lon_step=None)
    geo_line1 = create_geodesic((-89.9,0), (90,0), radius=1.0, n_points=40)
    geo_line1_dashed = create_geodesic((-90.1,0), (90,0), radius=1.0, n_points=60)
    geo_line1_dashed = make_dashed_line(geo_line1_dashed, dash_length=3)
    geo_line2 = create_geodesic((-89.9,90), (90,90), radius=1.0, n_points=40)
    geo_line2_dashed = create_geodesic((-90.1,90), (90,90), radius=1.0, n_points=60)
    geo_line2_dashed = make_dashed_line(geo_line2_dashed, dash_length=2)

    p = pv.Plotter()
    p.add_mesh(mesh1, color="grey")
    p.add_mesh(mesh2, color="red", line_width=4)
    p.add_mesh(geo_line1, color="blue", line_width=4)
    p.add_mesh(geo_line1_dashed, color="blue", line_width=4)
    p.add_mesh(geo_line2, color="green", line_width=4)
    p.add_mesh(geo_line2_dashed, color="green", line_width=4)
    p.show()