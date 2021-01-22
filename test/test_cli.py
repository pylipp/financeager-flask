import os
import tempfile
import time
import unittest
from threading import Thread
from unittest import mock

from financeager import (DEFAULT_TABLE, cli, clients, config, entries,
                         setup_log_file_handler)
from requests import RequestException, Response
from requests import get as requests_get

from financeager_flask import fflask, main

TEST_CONFIG_FILEPATH = "/tmp/financeager-test-config"
TEST_DATA_DIR = tempfile.mkdtemp(prefix="financeager-")
setup_log_file_handler(log_dir=TEST_DATA_DIR)


class CliTestCase(unittest.TestCase):
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
        if command not in ["copy", "pockets"]:
            args.extend(["--pocket", str(self.pocket)])

        args.extend(["--config-filepath", TEST_CONFIG_FILEPATH])

        sinks = clients.Client.Sinks(self.info, self.error)

        # Procedure similar to cli.main()
        params = cli._parse_command(args)
        plugins = [main.main()]
        configuration = config.Configuration(
            params.pop("config_filepath"), plugins=plugins)
        exit_code = cli.run(
            sinks=sinks, configuration=configuration, plugins=plugins, **params)

        # Get first of the args of the call of specified log method
        response = getattr(self, log_method).call_args[0][0]

        # Verify exit code
        self.assertEqual(exit_code,
                         cli.SUCCESS if log_method == "info" else cli.FAILURE)

        # Immediately return str messages
        if isinstance(response, str):
            return response

        # Convert Exceptions to string
        if isinstance(response, Exception):
            return str(response)

        if command in ["add", "update", "remove", "copy"]:
            return response["id"]

        if command in ["get", "list", "pockets"] and log_method == "info":
            return cli._format_response(
                response,
                command,
                default_category=configuration.get_option(
                    "FRONTEND", "default_category"))

        return response


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
host = http://{}
""".format(HOST_IP)

    @staticmethod
    def launch_server():
        # Patch DATA_DIR inside the thread to avoid having it
        # created/interfering with logs on actual machine
        import financeager
        financeager.DATA_DIR = TEST_DATA_DIR
        app = fflask.create_app(
            data_dir=TEST_DATA_DIR,
            config={
                "DEBUG": False,  # reloader can only be run in main thread
                "SERVER_NAME": CliFlaskTestCase.HOST_IP,
            })

        def shutdown():
            from flask import request
            app._server.run('stop')
            request.environ.get("werkzeug.server.shutdown")()
            return ""

        # For testing, add rule to shutdown Flask app
        app.add_url_rule("/stop", "stop", shutdown)

        app.run()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.flask_thread = Thread(target=cls.launch_server)
        cls.flask_thread.start()

        # wait for flask server being launched
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        # Invoke shutting down of Flask app
        requests_get("http://{}/stop".format(cls.HOST_IP))

    def test_add_list_remove(self):
        entry_id = self.cli_run("add cookies -100")

        response = self.cli_run("list")
        self.assertIn(entries.CategoryEntry.DEFAULT_NAME, response.lower())

        remove_entry_id = self.cli_run("remove {}", format_args=entry_id)
        self.assertEqual(remove_entry_id, entry_id)

        response = self.cli_run("pockets")
        self.assertIn(str(self.pocket), response)

    def test_add_get_remove_via_eid(self):
        entry_id = self.cli_run("add donuts -50 -c sweets")

        response = self.cli_run("get {}", format_args=entry_id)
        name = response.split("\n")[0].split()[2]
        self.assertEqual(name, "Donuts")

        self.cli_run("remove {}", format_args=entry_id)

        response = self.cli_run("list")
        self.assertEqual(response, "")

    def test_add_invalid_entry_table_name(self):
        response = self.cli_run(
            "add stuff 11.11 -t unknown", log_method="error")
        self.assertIn("400", response)

    def test_update(self):
        entry_id = self.cli_run("add donuts -50 -c sweets")

        update_entry_id = self.cli_run(
            "update {} -n bretzels", format_args=entry_id)
        self.assertEqual(entry_id, update_entry_id)

        response = self.cli_run("get {}", format_args=entry_id)
        self.assertIn("Bretzels", response)

    def test_update_nonexisting_entry(self):
        response = self.cli_run("update -1 -n a", log_method="error")
        self.assertIn("404", response)

    def test_get_nonexisting_entry(self):
        response = self.cli_run("get -1", log_method="error")
        self.assertIn("404", response)

    def test_remove_nonexisting_entry(self):
        response = self.cli_run("remove 0", log_method="error")
        self.assertIn("404", response)

    def test_recurrent_entry(self):
        entry_id = self.cli_run("add cookies -10 -c food -t recurrent -f "
                                "half-yearly -s 2020-01-01 -e 2020-12-31")
        self.assertEqual(entry_id, 1)

        response = self.cli_run("get {} -t recurrent", format_args=entry_id)
        self.assertIn("Half-Yearly", response)

        update_entry_id = self.cli_run(
            "update {} -t recurrent -n clifbars -f quarter-yearly",
            format_args=entry_id)
        self.assertEqual(update_entry_id, entry_id)

        response = self.cli_run("list")
        self.assertEqual(response.count("Clifbars"), 4)
        self.assertEqual(response.count("{}\n".format(entry_id)), 4)
        self.assertEqual(len(response.splitlines()), 10)

        self.cli_run("remove {} -t recurrent", format_args=entry_id)

        response = self.cli_run("list")
        self.assertEqual(response, "")

    def test_copy(self):
        destination_pocket = self.pocket + 1
        self.__class__.pocket += 1

        source_entry_id = self.cli_run("add donuts -50 -c sweets")

        destination_entry_id = self.cli_run(
            "copy {} -s {} -d {}",
            format_args=(source_entry_id, self.pocket, destination_pocket))

        # Swap pocket to trick cli_run()
        self.pocket, destination_pocket = destination_pocket, self.pocket
        destination_printed_content = self.cli_run(
            "get {}", format_args=destination_entry_id).splitlines()
        self.pocket, destination_pocket = destination_pocket, self.pocket

        source_printed_content = self.cli_run(
            "get {}", format_args=source_entry_id).splitlines()
        # Remove date lines
        destination_printed_content.remove(destination_printed_content[2])
        source_printed_content.remove(source_printed_content[2])
        self.assertListEqual(destination_printed_content,
                             source_printed_content)

    def test_copy_nonexisting_entry(self):
        destination_pocket = self.pocket + 1
        self.__class__.pocket += 1

        response = self.cli_run(
            "copy 0 -s {} -d {}",
            log_method="error",
            format_args=(self.pocket, destination_pocket))
        self.assertIn("404", response)

    def test_default_category(self):
        entry_id = self.cli_run("add car -9999")

        # Default category is converted for frontend display
        response = self.cli_run("list")
        self.assertIn(entries.CategoryEntry.DEFAULT_NAME, response.lower())

        # Category field is converted to 'None' and filtered for
        response = self.cli_run("list --filters category=unspecified")
        self.assertIn(entries.CategoryEntry.DEFAULT_NAME, response.lower())

        # The pattern is used for regex filtering; nothing is found
        response = self.cli_run("list --filters category=lel")
        self.assertEqual(response, "")

        # Default category is converted for frontend display
        response = self.cli_run("get {}", format_args=entry_id)
        self.assertEqual(response.splitlines()[-1].split()[1].lower(),
                         entries.CategoryEntry.DEFAULT_NAME)

    def test_communication_error(self):
        with mock.patch("requests.get") as mocked_get:
            response = Response()
            response.status_code = 500
            mocked_get.return_value = response
            response = self.cli_run("list", log_method="error")
            self.assertIn("500", response)

    @mock.patch("financeager_flask.offline.OFFLINE_FILEPATH",
                os.path.join(TEST_DATA_DIR, "financeager-test-offline.json"))
    def test_offline_feature(self):
        with mock.patch("requests.post") as mocked_post:
            # Try do add an item but provoke CommunicationError
            mocked_post.side_effect = RequestException("did not work")

            self.cli_run("add veggies -33", log_method="error")

            # Output from caught CommunicationError
            self.assertEqual("Error sending request: did not work",
                             str(self.error.call_args_list[0][0][0]))
            self.assertEqual("Stored 'add' request in offline backup.",
                             self.info.call_args_list[0][0][0])

            # Now request a print, and try to recover the offline backup
            # But adding is still expected to fail
            mocked_post.side_effect = RequestException("still no works")
            self.cli_run("list", log_method="error")
            # Output from print; expect empty database
            self.assertEqual({"elements": {
                DEFAULT_TABLE: {},
                "recurrent": {}
            }}, self.info.call_args_list[0][0][0])

            # Output from cli module
            self.assertEqual("Offline backup recovery failed!",
                             self.error.call_args_list[-1][0][0])

        # Without side effects, recover the offline backup
        self.cli_run("list")

        # Output from list command
        self.assertEqual({"elements": {
            DEFAULT_TABLE: {},
            "recurrent": {}
        }}, self.info.call_args_list[0][0][0])
        # Output from recovered add command
        self.assertEqual({"id": 1}, self.info.call_args_list[1][0][0])
        self.assertEqual("Recovered offline backup.",
                         self.info.call_args_list[2][0][0])


if __name__ == "__main__":
    unittest.main()
