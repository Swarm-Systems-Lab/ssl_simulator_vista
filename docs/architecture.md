# Architecture

This page describes how `ssl_vista` runs from CLI command to frame rendering.

## High-level flow

1. `sslvista` CLI parses arguments (`src/ssl_vista/cli.py`)
2. `run_app(...)` creates the Qt application (`src/ssl_vista/app.py`)
3. `MainWindow` loads layout and optional CSV (`src/ssl_vista/ui/main_window.py`)
4. Layout JSON is schema-validated (`src/ssl_vista/ui/layout.py`)
5. `SimulationGrid` builds plotter widgets from validated config (`src/ssl_vista/ui/grid.py`)
6. Plotter classes are resolved via registry (`src/ssl_vista/plotters/registry.py`)
7. Plotters set up scenes and update per frame (`src/ssl_vista/plotters/*`)

## Main components

## `cli.py`

Responsibilities:

- expose `run` command options
- list available layouts and sample datasets
- resolve names/paths through `DataManager`
- toggle debug flags via `CONFIG`
- launch Qt runtime through `run_app`

## `data_manager.py`

`DataManager` resolves package data paths and lists bundled resources:

- `grid_layouts/*.json`
- `samples/*.csv`
- `assets/*.ply`

It supports fallback to file paths when a bundled name is not found.

## `MainWindow`

Core runtime orchestration:

- owns toolbar and central `SimulationGrid`
- loads simulation data via `ssl_simulator.load_sim`
- drives playback state (`playing`, current frame index)
- updates all plotters through timer callbacks

Playback/event loop summary:

- toolbar and keyboard update the time slider
- slider change calls `update_time`
- `update_time` calls `update_simulation`
- `update_simulation` calls `grid.update_scenes(sim_data, idx)`

## `SimulationGrid`

`SimulationGrid` is a widget container with:

- splitters for row/column layout
- an array of plotter objects
- a shared timer for animation
- a context object (`SimulationGridContext`) for cross-plotter signals

The shared context currently exposes robot focus state and a `robot_focus_changed` signal.

## Plotter system

Base classes:

- `_BasePlotter`: generic Qt widget integration and lifecycle contract
- `_BaseVisualPlotter`: PyVista-backed implementation with scene-object support
- `BaseCanvasPlotter`: canvas/grid + robot helpers
- `BaseMplPlotter`: Matplotlib figure/canvas lifecycle

Built-in plotters:

- `Plotter2DCanvas`
- `Plotter3DCanvas`
- `Plotter3DAttitude`

Custom Matplotlib plotters can be loaded dynamically from a Python file via layout entries (`module_path`, `class_name`).

## Scene object model

PyVista scene composition uses:

- `SceneObject`
- `SceneObjectGroup`

These abstractions manage mesh + actor lifecycle and group hierarchical scene elements.

## Configuration

Canvas-plotter configuration is grouped into typed pydantic models in
`src/ssl_vista/plotters/pv_utils/configs.py` — `GridConfig`, `CameraConfig`,
`GraphicsConfig`, `RobotConfig`. A plotter accepts each as a `grid`/`camera`/`robot`/
`graphics` namespace (a model or a plain dict, e.g. from a layout's `args`) and forwards
it whole to its sub-component, so options never need re-declaring on parent classes.

`src/ssl_vista/config.py` (`CONFIG`) is reserved for non-style global runtime flags.
