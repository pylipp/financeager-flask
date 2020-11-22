import time
import unittest

from financeager import config as cfg
from financeager import exceptions

from financeager_flask import main


class ConfigTestCase(unittest.TestCase):
    def test_load_custom_config_file(self):
        # create custom config file, modify service name
        filepath = "/tmp/{}".format(int(time.time()))
        with open(filepath, "w") as file:
            file.write("[SERVICE]\nname = flask\n")

        config = cfg.Configuration(filepath=filepath, plugins=[main.main()])
        self.assertEqual(config.get_option("SERVICE", "name"), "flask")

    def test_invalid_config(self):
        filepath = "/tmp/{}".format(int(time.time()))

        for content in ("[SERVICE:FLASK]\ntimeout = foo\n",):
            with open(filepath, "w") as file:
                file.write(content)
            self.assertRaises(
                exceptions.InvalidConfigError,
                cfg.Configuration,
                filepath=filepath,
                plugins=[main.main()],
            )


if __name__ == "__main__":
    unittest.main()
