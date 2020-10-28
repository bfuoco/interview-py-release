import logging
from glob import glob
from importlib import import_module
from inspect import getmembers, isfunction
from os import path
from .core import Task, TaskDef, TaskState

def get_release_tasks(state: TaskState) -> dict[str, TaskDef]:
    """Loads all release tasks that can be executed.

    Each release task exists as a separate module/python file in the tasks/ folder. Tasks must be
    formatted in a specific way in order to be executed.
    
    Review the Task class in the core.py library for more information.
    """
    log = state.root_logger.getChild("task")

    # we use an absolute path that is based on the task.py filename's location
    # instead of a relative path.
    #
    # when you import with the import keyword, you're protected by the package hierarchy if the
    # current working directory changes. we have no such protection here, so we do this so that
    # we're always trying to read from a directory relative to the task.py file.
    #
    task_dir = path.join(path.dirname(__file__), "tasks")
    task_pattern = path.join(task_dir, "[!_]*.py")

    log.debug(f"tasks directory is {task_dir}")
    log.debug(f"detecting tasks with glob pattern {task_pattern}")

    # this section of code uses importlib to import each task in the tasks folder, where each task
    # is a module in a separate python file.
    #
    # the task name is the file name minus the .py extension, ie:
    #   tasks/create_release_branch.py -> create_release_branch
    #
    # this allows more finger-grained control over the import process. it also allows us to add new
    # tasks simply by adding a new file to the tasks/ folder.
    #
    tasks = dict()
    for filename in glob(task_pattern):
        name = path.splitext(path.basename(filename))[0]
        log.debug(f"detected task {name} in {filename}")

        module = import_module(f".{name}", package="release_tools.tasks")
        if not hasattr(module, "Task"):
            raise NameError(f"task {name} does not define a top-level Task class")

        clz = getattr(module, "Task")

        if not issubclass(clz, Task):
            raise NameError(f"task {name} does not declare all required functions")

        tasks[name] = clz

    return tasks