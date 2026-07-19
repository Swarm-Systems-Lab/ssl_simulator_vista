"""Compatibility shim: the source contract lives in the ground data plane now.

`DataSource`/`LoggedSource`/`StreamSource` moved to **ssl_tmtc** so headless ground apps
(bridges, GCS tools, analysis) can consume data without installing the viewer stack. Import
from ``ssl_tmtc.sources`` in new code; this module keeps existing ``ssl_vista.sources``
imports working.
"""

from ssl_tmtc.sources import DataSource, LoggedSource, StreamSource

__all__ = ["DataSource", "LoggedSource", "StreamSource"]
