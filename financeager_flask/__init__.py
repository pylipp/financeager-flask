import os

from financeager import DATA_DIR

OFFLINE_FILEPATH = os.path.join(DATA_DIR, "offline.json")

# URL endpoints
POCKETS_TAIL = "/pockets"
COPY_TAIL = "/copy"

# HTTP communication defaults
DEFAULT_HOST = "http://127.0.0.1:5000"
DEFAULT_TIMEOUT = 10
