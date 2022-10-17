import os
import tempfile
import unittest
from collections import defaultdict
from unittest import mock
from urllib.parse import urlsplit

import requests
import responses
from financeager import (
    DEFAULT_TABLE,
    RECURRENT_TABLE,
    cli,
    clients,
    config,
    setup_log_file_handler,
)
from requests import RequestException

from financeager_flask import flask, httprequests, main, version

TEST_CONFIG_FILEPATH = "/tmp/financeager-test-config"
TEST_DATA_DIR = tempfile.mkdtemp(prefix="financeager-")
setup_log_file_handler(log_dir=TEST_DATA_DIR)


class CliTestCase(unittest.TestCase):
    test_interface = None

    @classmethod
    def setUpClass(cls):
        # Create test config file for client
        with open(TEST_CONFIG_FILEPATH, "w") as file:
            file.write(cls.CONFIG_FILE_CONTENT)

        cls.pocket = 1900

    def setUp(self):
        # Separate test runs by running individual test methods using distinct
        # pockets (especially crucial for CliFlaskTestCase which uses a single
        # Flask instance for all tests)
        self.__class__.pocket += 1

        # Mocks to record output of cli.run() call
        self.info = mock.MagicMock()
        self.error = mock.MagicMock()

    def cli_run(self, command_line, log_method="info", format_args=()):
        """Wrapper around cli.run() function. Adds convenient command line
        options (pocket and config filepath). Executes the actual run() function
        while patching the module logger info and error methods to catch their
        call arguments.

        'command_line' is a string of the form that financeager is called from
        the command line with. 'format_args' are optional objects that are
        formatted into the command line string. Must be passed as tuple if more
        than one.

        If information about an added/update/removed/copied element was to be
        logged, the corresponding ID is matched from the log call arguments to
        the specified 'log_method' and returned. Otherwise the raw log call is
        returned.
        """
        self.info.reset_mock()
        self.error.reset_mock()

        if not isinstance(format_args, tuple):
            format_args = (format_args,)
        args = command_line.format(*format_args).split()
        command = args[0]

        # Exclude option from subcommand parsers that would be confused
        if command not in ["copy", "pockets", "web-version"]:
            args.extend(["--pocket", str(self.pocket)])

        args.extend(["--config-filepath", TEST_CONFIG_FILEPATH])

        sinks = clients.Client.Sinks(self.info, self.error)

        # Procedure similar to cli.main()
        plugin = main.main()
        plugin.client.proxy = httprequests.Proxy(interface=self.test_interface)
        plugins = [plugin]
        params = cli._parse_command(args, plugins=plugins)
        configuration = config.Configuration(
            params.pop("config_filepath"), plugins=plugins
        )
        exit_code = cli.run(
            sinks=sinks, configuration=configuration, plugins=plugins, **params
        )

        # Get first of the args of the call of specified log method
        response = getattr(self, log_method).call_args[0][0]

        # Verify exit code
        self.assertEqual(
            exit_code, cli.SUCCESS if log_method == "info" else cli.FAILURE
        )

        # Immediately return str messages
        if isinstance(response, str):
            return response

        # Convert Exceptions to string
        if isinstance(response, Exception):
            return str(response)

        if command in ["add", "update", "remove", "copy"]:
            return response["id"]

        if command in ["get", "pockets"] and log_method == "info":
            return cli._format_response(
                response,
                command,
                default_category=configuration.get_option(
                    "FRONTEND", "default_category"
                ),
                recurrent_only=params.get("recurrent_only", False),
            )

        if command == "list" and log_method == "info":
            return response

        return response


class TestInterface:
    """Utility interface to enable thorough testing of the entire stack."""

    def __init__(self, test_app):
        self.client = test_app.test_client()

    def get(self, url, **kwargs):
        return self._request("get", url=url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("post", url=url, **kwargs)

    def patch(self, url, **kwargs):
        return self._request("patch", url=url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request("delete", url=url, **kwargs)

    def _request(self, method, *, url, **kwargs):
        """Obtain URL path and send request to Flask test app (this covers the entire
        back-end). Use the returned JSON to construct a mock response and register it.
        Use the `requests` interface to simulate issuing the actual request from the
        front-end.
        """
        # Remove kwargs which are not recognized by Flask test client
        test_kwargs = kwargs.copy()
        del test_kwargs["auth"]
        del test_kwargs["timeout"]
        url_tail = urlsplit(url).path
        response = getattr(self.client, method)(url_tail, **test_kwargs)

        responses.add(
            method.upper(), url, json=response.json, status=response.status_code
        )
        return requests.request(method, url, **kwargs)


@mock.patch("financeager.DATA_DIR", TEST_DATA_DIR)
class CliFlaskTestCase(CliTestCase):
    HOST_IP = "127.0.0.1:5000"
    CONFIG_FILE_CONTENT = """\
[SERVICE]
name = flask

[FRONTEND]
default_category = unspecified
date_format = %%m-%%d

[SERVICE:FLASK]
host = ""
"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        app = flask.create_app(
            data_dir=TEST_DATA_DIR,
            config={
                # "DEBUG": False,  # reloader can only be run in main thread
                "SERVER_NAME": CliFlaskTestCase.HOST_IP,
            },
        )
        cls.test_interface = TestInterface(app)

    @classmethod
    def tearDownClass(cls):
        cls.test_interface = None

    @responses.activate
    def test_add_list_remove(self):
        entry_id = self.cli_run("add cookies -100")

        response = self.cli_run("list")["elements"]
        self.assertIsNone(response[DEFAULT_TABLE][str(entry_id)]["category"])

        remove_entry_id = self.cli_run("remove {}", format_args=entry_id)
        self.assertEqual(remove_entry_id, entry_id)

    @unittest.skipIf(os.getenv("CI", "false") == "true", reason="Failing in CI")
    @responses.activate
    def test_pockets(self):
        response = self.cli_run("pockets")
        self.assertIn(str(self.pocket - 1), response)

    @responses.activate
    def test_add_get_remove_via_eid(self):
        entry_id = self.cli_run("add donuts -50 -c sweets")

        response = self.cli_run("get {}", format_args=entry_id)
        name = response.split("\n")[0].split()[2]
        self.assertEqual(name, "Donuts")

        self.cli_run("remove {}", format_args=entry_id)

        response = self.cli_run("list")["elements"]
        self.assertEqual(
            response, {DEFAULT_TABLE: {}, RECURRENT_TABLE: defaultdict(list)}
        )

    @responses.activate
    def test_add_invalid_entry_table_name(self):
        response = self.cli_run("add stuff 11.11 -t unknown", log_method="error")
        self.assertIn("400", response)

    @responses.activate
    def test_update(self):
        entry_id = self.cli_run("add donuts -50 -c sweets")

        update_entry_id = self.cli_run("update {} -n bretzels", format_args=entry_id)
        self.assertEqual(entry_id, update_entry_id)

        response = self.cli_run("get {}", format_args=entry_id)
        self.assertIn("Bretzels", response)

    @responses.activate
    def test_update_nonexisting_entry(self):
        response = self.cli_run("update -1 -n a", log_method="error")
        self.assertIn("404", response)

    @responses.activate
    def test_get_nonexisting_entry(self):
        response = self.cli_run("get -1", log_method="error")
        self.assertIn("404", response)

    @responses.activate
    def test_remove_nonexisting_entry(self):
        response = self.cli_run("remove 0", log_method="error")
        self.assertIn("404", response)

    @responses.activate
    def test_recurrent_entry(self):
        entry_id = self.cli_run(
            "add cookies -10 -c food -t recurrent -f "
            "half-yearly -s 2020-01-01 -e 2020-12-31"
        )
        self.assertEqual(entry_id, 1)

        response = self.cli_run("get {} -t recurrent", format_args=entry_id)
        self.assertIn("Half-Yearly", response)

        update_entry_id = self.cli_run(
            "update {} -t recurrent -n clifbars -f quarter-yearly", format_args=entry_id
        )
        self.assertEqual(update_entry_id, entry_id)

        response = self.cli_run("list")["elements"]
        self.assertEqual(len(response[RECURRENT_TABLE][str(update_entry_id)]), 4)

        self.cli_run("remove {} -t recurrent", format_args=entry_id)

        response = self.cli_run("list")["elements"]
        self.assertEqual(
            response, {DEFAULT_TABLE: {}, RECURRENT_TABLE: defaultdict(list)}
        )

    @responses.activate
    def test_copy(self):
        destination_pocket = self.pocket + 1
        self.__class__.pocket += 1

        source_entry_id = self.cli_run("add donuts -50 -c sweets")

        destination_entry_id = self.cli_run(
            "copy {} -s {} -d {}",
            format_args=(source_entry_id, self.pocket, destination_pocket),
        )

        # Swap pocket to trick cli_run()
        self.pocket, destination_pocket = destination_pocket, self.pocket
        destination_printed_content = self.cli_run(
            "get {}", format_args=destination_entry_id
        ).splitlines()
        self.pocket, destination_pocket = destination_pocket, self.pocket

        source_printed_content = self.cli_run(
            "get {}", format_args=source_entry_id
        ).splitlines()
        # Remove date lines
        destination_printed_content.remove(destination_printed_content[2])
        source_printed_content.remove(source_printed_content[2])
        self.assertListEqual(destination_printed_content, source_printed_content)

    @responses.activate
    def test_copy_nonexisting_entry(self):
        destination_pocket = self.pocket + 1
        self.__class__.pocket += 1

        response = self.cli_run(
            "copy 0 -s {} -d {}",
            log_method="error",
            format_args=(self.pocket, destination_pocket),
        )
        self.assertIn("404", response)

    @responses.activate
    @mock.patch(
        "financeager_flask.offline.OFFLINE_FILEPATH",
        os.path.join(TEST_DATA_DIR, "financeager-test-offline.json"),
    )
    def _test_offline_feature(self):
        with mock.patch("requests.post") as mocked_post:
            # Try do add an item but provoke CommunicationError
            mocked_post.side_effect = RequestException("did not work")

            self.cli_run("add veggies -33", log_method="error")

            # Output from caught CommunicationError
            self.assertEqual(
                "Error sending request: did not work",
                str(self.error.call_args_list[0][0][0]),
            )
            self.assertEqual(
                "Stored 'add' request in offline backup.",
                self.info.call_args_list[0][0][0],
            )

            # Now request a print, and try to recover the offline backup
            # But adding is still expected to fail
            mocked_post.side_effect = RequestException("still no works")
            self.cli_run("list", log_method="error")
            # Output from print; expect empty database
            self.assertEqual(
                {"elements": {DEFAULT_TABLE: {}, "recurrent": {}}},
                self.info.call_args_list[0][0][0],
            )

            # Output from cli module
            self.assertEqual(
                "Offline backup recovery failed!", self.error.call_args_list[-1][0][0]
            )

        # Without side effects, recover the offline backup
        self.cli_run("list")

        # Output from list command
        self.assertEqual(
            {"elements": {DEFAULT_TABLE: {}, "recurrent": {}}},
            self.info.call_args_list[0][0][0],
        )
        # Output from recovered add command
        self.assertEqual({"id": 1}, self.info.call_args_list[1][0][0])
        self.assertEqual("Recovered offline backup.", self.info.call_args_list[2][0][0])

    @unittest.skipIf(os.getenv("CI", "false") == "true", reason="Failing in CI")
    @responses.activate
    def test_web_version(self):
        response = self.cli_run("web-version")
        self.assertIn(version(), response)

    @responses.activate
    def test_list_recurrent_only(self):
        self.cli_run("add rent -500 -f monthly")
        response = self.cli_run("list --recurrent-only")
        self.assertEqual(response["elements"][0]["name"], "rent")
        self.assertEqual(response["elements"][0]["frequency"], "monthly")


@mock.patch("financeager.DATA_DIR", TEST_DATA_DIR)
class CliErrorTestCase(CliTestCase):

    HOST_IP = "127.0.0.1:5000"
    CONFIG_FILE_CONTENT = """\
[SERVICE]
name = flask

[FRONTEND]
default_category = unspecified
date_format = %%m-%%d

[SERVICE:FLASK]
host = ""
"""

    @responses.activate
    def test_communication_error(self):
        responses.get(f"http://{self.HOST_IP}/pockets/{self.pocket}", status=500)
        response = self.cli_run("list", log_method="error")
        self.assertIn("Internal Server Error (500)", response)


if __name__ == "__main__":
    unittest.main()
