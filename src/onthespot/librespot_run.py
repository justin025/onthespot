import os
import logging

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

try:
    from . import librespot_patch  # noqa: F401
except Exception as e:
    logging.getLogger("onthespot.librespot_run").warning(
        "Failed to import librespot_patch: %s", e
    )
