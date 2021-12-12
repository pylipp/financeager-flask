import os

from financeager import DATA_DIR

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

OFFLINE_FILEPATH = os.path.join(DATA_DIR, "offline.json")

# URL endpoints
POCKETS_TAIL = "/pockets"
COPY_TAIL = "/copy"
VERSION_TAIL = "/version"

# HTTP communication defaults
DEFAULT_HOST = "http://127.0.0.1:5000"
DEFAULT_TIMEOUT = 10


def version(package_name=__package__):
    return importlib_metadata.version(package_name)
