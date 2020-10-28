import logging
import sys
from argparse import ArgumentParser
from .core import TaskState, get_current_release, get_available_releases
from .task import get_release_tasks

def run(argv=sys.argv[1:]):
    # we parse the log level early here. this is because of two conflicting requirements:
    #
    #   1.  we need to parse the tasks folder in order to determine valid argument values
    #       for the tasks argument.
    #   2.  we want to have logging setup before we parse the tasks folder so that we can
    #       debug any issues with loading tasks.
    #
    # to accommodate this, we validate the log level first and ignore any other arguments.
    # once the tasks are loaded, we can then validate the entire set of arguments.
    #
    #
    # this messes with the --help argument though, so it's not a perfect solution. another option
    # would be to queue all log output until the log level is known, then empty the queue after the
    # log level is specified. 
    #
    LOG_LEVELS = {
        "fatal": logging.CRITICAL,
        "error": logging.ERROR,
        "warn": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }

    parser = ArgumentParser(description="Performs tasks associated with a release.", allow_abbrev=False)
    parser.add_argument("--log-level", choices=LOG_LEVELS.keys(), default="info")

    # discard unknown args for now
    #
    args, _ = parser.parse_known_args()

    logging.basicConfig(
        level=LOG_LEVELS[args.log_level],
        format="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    log = logging.getLogger("release")
    state = TaskState(
        root_logger=log,
        current_release=get_current_release(),
        available_releases=get_available_releases())

    # loads all the tasks from the tasks folder.
    # 
    # the tasks.py module guarantees that all returned tasks will be in the correct format to be
    # consumed by the harness.
    #
    tasks = get_release_tasks(state)
    task_names = tasks.keys()

    log.info(f"loaded {len(tasks)} tasks: {', '.join(task_names)}")

    # this would probably work better if each task operated as a sub parser, then
    # they could have their own arguments, ie:
    # 
    #   release.py create-release-branch --branch-prefix=release/
    #
    parser = ArgumentParser(description="Performs tasks associated with a release.")
    parser.add_argument("--tasks", nargs="+", choices=task_names, default=task_names)
    parser.add_argument("--log-level", choices=LOG_LEVELS.keys(), default="info")

    args = parser.parse_args()

    # following is the main portion of the harness that executes release tasks. simply, just run
    # though each task that the user specified on the command line and execute it.
    #
    for name in args.tasks:
        task = tasks[name]

        log.info(f'running task {name}')
        task.run(state)
        log.info(f'successfully completed task {name}')
