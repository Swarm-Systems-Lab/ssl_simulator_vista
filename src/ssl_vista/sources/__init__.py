"""Compatibility shim: the source contract lives in the ground data plane now.

`DataSource`/`LoggedSource`/`StreamSource` moved to **ssl_link** so headless ground apps
(bridges, GCS tools, analysis) can consume data without installing the viewer stack. Import
from ``ssl_link.sources`` in new code; this module keeps existing ``ssl_vista.sources``
imports working.
"""

from ssl_link.sources import DataSource, LoggedSource, StreamSource

__all__ = ["DataSource", "LoggedSource", "StreamSource"]
