import financeager
from financeager import clients
from financeager import exceptions as base_exceptions
from financeager import plugin

from . import DEFAULT_HOST, DEFAULT_TIMEOUT, exceptions, httprequests, offline

SERVICE_NAME = "flask"
CONFIG_SECTION_NAME = "SERVICE:{}".format(SERVICE_NAME.upper())


class _Configuration(plugin.PluginConfiguration):
    def init_defaults(self, config_parser):
        config_parser[CONFIG_SECTION_NAME] = {
            "host": DEFAULT_HOST,
            "timeout": DEFAULT_TIMEOUT,
            "username": "",
            "password": "",
        }

    def init_option_types(self, option_types):
        option_types[CONFIG_SECTION_NAME] = {
            "timeout": "int",
        }


class _CliOptions(plugin.PluginCliOptions):
    def extend(self, command_parser):
        command_parser.add_parser(
            "web-version",
            help="information about financeager versions installed on server "
            "(only if configured with service name '{}')".format(SERVICE_NAME),
        )


class _Client(clients.Client):
    """Client for communicating with the financeager Flask webservice."""

    def __init__(self, *, configuration, sinks):
        """Set up proxy and urllib3 logger."""
        super().__init__(configuration=configuration, sinks=sinks)
        self.proxy = httprequests.Proxy(
            http_config=configuration.get_section(CONFIG_SECTION_NAME)
        )

        financeager.init_logger("urllib3")

    def safely_run(self, command, **params):
        """Execute base functionality.
        If successful, attempt to recover offline backup. Otherwise store
        request in offline backup.
        Return whether execution was successful.

        :return: bool
        """
        success = super().safely_run(command, **params)

        if success:
            try:
                # Avoid recursion by passing base class for invoking safely_run
                if offline.recover(super()):
                    self.sinks.info("Recovered offline backup.")

            except exceptions.OfflineRecoveryError:
                self.sinks.error("Offline backup recovery failed!")
                success = False

        # If request was erroneous, it's not supposed to be stored offline
        if (
            not isinstance(self.latest_exception, base_exceptions.InvalidRequest)
            and self.latest_exception is not None
            and offline.add(command, **params)
        ):
            self.sinks.info("Stored '{}' request in offline backup.".format(command))

        return success


def main():
    return plugin.ServicePlugin(
        name=SERVICE_NAME,
        client=_Client,
        config=_Configuration(),
        cli_options=_CliOptions(),
    )
