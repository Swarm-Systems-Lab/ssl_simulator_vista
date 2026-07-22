"""ssl-vista in the data-plane pipeline: sim -> UDP datagrams -> UdpSource -> live viewer.

The full chain this demonstrates::

    Engine(sink=udp_sink())  --datagrams-->  UdpSource (a DataSource)  -->  vista follows live

Run everything in one command (producer thread + viewer window)::

    uv run python examples/live_udp_viewer.py

Or split the ends -- start the viewer first and watch it sit empty until frames arrive
(deferred scene init), or start it late and join mid-flight like a ground station meeting a
vehicle already flying. Terminals, or different machines with ``--host``::

    uv run python examples/live_udp_viewer.py produce
    uv run python examples/live_udp_viewer.py view

In the window: the view chases the stream head; grab the slider to scrub buffered history
(detaches), press Play to re-attach to live.
"""

import sys
import threading
import time as wall

import numpy as np
from ssl_simulator import Engine, IntegrationSystem, System, World, set_log_level
from ssl_link.sources import UdpSource
from ssl_link.transports import udp_sink

set_log_level("WARNING")

PORT = 47600
LOG_DT = 0.05  # 20 Hz streaming, smooth enough to watch
DURATION = 30.0


class Orbit(System):
    """Drones circle the origin at different rates -- visibly alive in a 2D canvas."""

    reads = ("p", "rate")
    writes = ("u",)

    def run(self, world, dt):
        p, rate = world["p"], world["rate"]
        world["u"][:, 0] = -rate * p[:, 1]
        world["u"][:, 1] = rate * p[:, 0]


def build_world(n=5):
    world = World(n)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    world.add_state("p", dim=2, init=np.stack([np.cos(angles), np.sin(angles)], axis=1) * 3)
    world.add("u", dim=2)
    world.add("rate", init=np.linspace(0.5, 1.5, n))
    world.add_system(Orbit())
    world.add_system(IntegrationSystem([("p", "u")]))
    return world


def build_grid_spec():
    """One 2D canvas; `single_integrator` robots need only the `p` component."""
    from ssl_vista.types import GridSpec, PlotterSpec

    return GridSpec(
        shape=(1, 1),
        plotters=[
            PlotterSpec(
                position=(0, 0),
                plotter_type="Plotter2DCanvas",
                kwargs={
                    "robot": {"type": "single_integrator", "color": "royalblue"},
                    "grid": {"range": 5},
                },
            )
        ],
    )


def produce(host="127.0.0.1"):
    print(f"publishing {DURATION:.0f}s of sim to udp://{host}:{PORT} ...")
    sink = udp_sink(host=host, port=PORT)

    def paced(t, frame):
        sink(t, frame)
        wall.sleep(LOG_DT / 2)  # ~2x real time; the wire is the pacing point

    Engine(time_step=0.01, log_time_step=LOG_DT, sink=paced).run(build_world(), DURATION, eta=False)
    print("producer done.")


def view():
    """The viewer end: a UdpSource is just a DataSource, so vista follows it live."""
    from ssl_vista import run_app

    source = UdpSource(port=PORT, capacity=2000).start()
    print(f"viewer listening on udp://0.0.0.0:{PORT} -- window follows frames as they arrive.")
    run_app(grid_spec=build_grid_spec(), sim_data=source, sim_settings=source.settings)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "127.0.0.1"
    if mode == "produce":
        produce(host)
    elif mode == "view":
        view()
    else:
        threading.Thread(target=produce, daemon=True).start()
        view()


if __name__ == "__main__":
    main()
