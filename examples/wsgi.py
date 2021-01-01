# This is an examplatory WSGI configuration file. I use it to run financeager on
# pythonanywhere.
# It is assumed that the financeager project is cloned to the home directory and
# all requirements are installed.

import os
import sys

from financeager_flask import DATA_DIR
from financeager_flask.fflask import create_app

path = os.path.expanduser('~/financeager-flask/financeager_flask/fflask.py')
if path not in sys.path:
    sys.path.append(path)

# the 'application' object will be used by the WSGI server
application = create_app(
    data_dir=DATA_DIR,
    config={"DEBUG": True},
)
