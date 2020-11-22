"""Utilities to create flask webservice."""
import os

from financeager import (init_logger, make_log_stream_handler_verbose, server,
                         setup_log_file_handler)
from flask import Flask
from flask_restful import Api

from . import COPY_TAIL, PERIODS_TAIL, resources

logger = init_logger(__name__)


def create_app(data_dir=None, config=None):
    """Create web app with RESTful API built from resources. The function is
    named such that the flask cli detects it as app factory method.
    The log file handler is set up very first.
    If 'data_dir' or the environment variable 'FINANCEAGER_FLASK_DATA_DIR' is
    given, a directory is created to store application data.
    An instance of 'server.Server' is created, passing 'data_dir'. If 'data_dir'
    is not given, the application data is stored in memory and will be lost when
    the app terminates.
    'config' is a dict of configuration variables that flask understands.
    """
    setup_log_file_handler()

    # Propagate flask and werkzeug log messages to financeager logs
    init_logger("flask.app")
    init_logger("werkzeug")

    app = Flask(__name__)
    app.config.update(config or {})
    if app.debug:
        make_log_stream_handler_verbose()

    data_dir = data_dir or os.environ.get("FINANCEAGER_FLASK_DATA_DIR")
    if data_dir is None:
        logger.warning("'data_dir' not given. Application data is stored in "
                       "memory and is lost when the flask app terminates. Set "
                       "the environment variable FINANCEAGER_FLASK_DATA_DIR "
                       "accordingly for persistent data storage.")
    else:
        os.makedirs(data_dir, exist_ok=True)

    logger.debug("Created flask app {} - {} mode".format(
        app.name, "debug" if app.debug else "production"))

    srv = server.Server(data_dir=data_dir)
    logger.debug(
        "Started financeager server with data dir '{}'".format(data_dir))

    api = Api(app)
    api.add_resource(
        resources.PeriodsResource, PERIODS_TAIL, resource_class_args=(srv,))
    api.add_resource(
        resources.CopyResource, COPY_TAIL, resource_class_args=(srv,))
    api.add_resource(
        resources.PeriodResource,
        "{}/<period_name>".format(PERIODS_TAIL),
        resource_class_args=(srv,))
    api.add_resource(
        resources.EntryResource,
        "{}/<period_name>/<table_name>/<eid>".format(PERIODS_TAIL),
        resource_class_args=(srv,))

    # Assign attribute such that e.g. test_cli can access Server methods
    app._server = srv

    return app
