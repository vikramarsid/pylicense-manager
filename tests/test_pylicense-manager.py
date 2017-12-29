# coding=utf-8
import unittest

import os

from pylicense_manager.cli import main
from pylicense_manager.manager import Manager

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
requirements_file = os.path.realpath(os.path.join(SCRIPT_DIR, 'requirements.txt'))


class TestPyLicenseManager(unittest.TestCase):

    def setUp(self):
        self.manager = Manager(requirements_path=requirements_file, output_path=SCRIPT_DIR,
                               gh_token="ef3252e5d7ffadbbae1edfa69ee215b7e6488d88")

    def test_cli_help(self):
        options = ["-h"]
        self.assertTrue(main(options))

    def test_create_directory_structure(self):
        self.assertTrue(self.manager._create_directory_structure())

    def test_parse_requirements(self):
        package_details = self.manager.parse_requirements()
        # print package_details


if __name__ == '__main__':
    unittest.main()
