# coding=utf-8
"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -m pylicense-manager` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``pylicense-manager.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``pylicense-manager.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import logging
import sys
import traceback
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import os

from pylicense_manager.manager import Manager

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_PATH = os.path.realpath(os.path.join(SCRIPT_DIR, '../../'))
logger = logging.getLogger(__name__)

# Setup argument parser
parser = ArgumentParser(
    description="Python requirements license generator",
    formatter_class=RawDescriptionHelpFormatter)
parser.add_argument(
    '-r', "--requirements",
    dest="requirements_file",
    help="path to requirements.txt",
    metavar="requirements_file",
    nargs='?', const=BASE_PATH, type=str,
    default=BASE_PATH)
parser.add_argument(
    "-o", "--outputDirectory",
    dest="output_path",
    help="paths to put generated licenses [default: %(default)s]",
    metavar="output_path",
    default=BASE_PATH)
parser.add_argument(
    "-a", "--github-token",
    dest="gh_token",
    help="generate global statistics",
    metavar="gh_token",
    default=None)
parser.add_argument(
    "-v", "--verbose",
    dest="verbose",
    action="count",
    help="set verbosity level",
    default=0)


def main(args=None):
    if args is None:
        arguments = sys.argv
    else:
        arguments = sys.argv
        arguments.extend(args)

    # if no arguments
    if len(arguments) == 2:
        parser.print_help()
        sys.exit(0)

    program_name = os.path.basename(arguments[1])
    try:
        args = parser.parse_args()
        reqs_path = args.requirements
        output_path = args.output_path
        gh_token = args.gh_token
        verbose = args.verbose

        if isinstance(verbose, int):
            if verbose > 0:
                logger.setLevel(logging.DEBUG)
                logger.debug("Verbose debug mode on")
            else:
                logger.setLevel(logging.INFO)
        logger.info("Source Path: %s", reqs_path)
        logger.info("Output Directory: %s", output_path)
        logger.info("verbosity level: %d", verbose)
        if reqs_path:
            logger.info("Generating licenses for passed requirements.txt: [%s]", reqs_path)
            manager = Manager(requirements_path=reqs_path, output_path=output_path, gh_token=gh_token)
            manager.parse_requirements()
            logger.info("Successfully generated license files")
        else:
            logger.info("Requirements not passed. Exiting!")

    except KeyboardInterrupt:
        return 0

    except (SystemExit, SystemError) as exit_code:
        return exit_code

    except Exception as exp:
        logger.debug("Caught Exception: %s\n", exp)
        traceback.print_exc()
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(exp) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        sys.exit(2)
