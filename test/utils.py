"""Utiliary classes for testing."""
from financeager import clients

from financeager_flask import main


class Client(clients.LocalServerClient):
    """Implementation that assigns dummy sinks to consume the client's output.
    The underlying Proxy is patched to store data in memory instead of in
    financeager.DATA_DIR.
    """

    def __init__(self):
        f = lambda s: None
        super().__init__(
            configuration=main._Configuration(),
            sinks=clients.Client.Sinks(f, f))

        self.proxy._pocket_kwargs["data_dir"] = None
