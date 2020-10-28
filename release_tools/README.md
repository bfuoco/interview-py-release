# Requirements

For the most part, this script uses the Python standard library, with the exception of the PyGithub
package for interacting with Github. The full requirements are:

- Python 3.9
- PyGithub

Python 3.9 is required because the script uses the new typehint feature where you can typehint with
built-in collection types of importing the corresponding type from the typing module, ie:

```python
def my_function(): -> list[str]
```

Instead of:

```python
from typing import List
def my_function(): -> List[str]
```

# Usage

Running the script without any command line parameters will execute all available tasks with the
INFO log level. Example:

```
python3 release.py 
```

There are also several command line parameters that you can specify that customize how the script
is run:

### `--log-level`

Specifying the severity level changes how many logs are displayed. For example, to view all debug
logs, you can execute the script like so:

```
python3 release.py --log-level=debug
```

The default log level, if left unspecified, is "info".

### `--task`

If you only want to run a specific task or subset of tasks, you can specify this with the --task 
parameter. This is useful if, for example, one or more of your tasks have already completed
successfully, and you only need to re-run a single task.

To run a single task:

```
python3 release.py --task==create_release_branch
```

To run multiple tasks, separate them with a comma:

```
python3 release.py --task=create_release_branch,increment_plist
```

# Extensibility

You can add additional tasks by creating a new python module in the tasks/ folder. The task will
have the same name as your module. As of right now, the only requirement is that the module
define a class named Task, with a single method named run.

For example, to create a new task named my_task, first add a new file named my_task.py to the tasks/
folder, so that your folder looks like this:

```
tasks\
    create_release_branch.py
    generate_feature_report.py
    increment_plist.py
    my_task.py
```

Next, add the following code to the my_task.py file:

```python
from ..core import TaskState

class Task():
    def run(state: TaskState) -> None:
        print('my task has run')
```

Once that file exists, the new task can be run on the command line, like so:

```bash
python3 release.py --task=my_task.py
```

# Caveats

One of the first things that I'd fix about this - if I was working on it further - would be to stop
reading files from the local repository. It makes sense to use core repo's master branch as the
single source of truth as to which releases are available and what is the current release.

The problem with the current approach of reading local files is that after the script runs, there
is no local knowledge of the repo state unless we pull down the changes. ie: if you run
"increment-plist" twice in a row, it will make two commits with the same version.

# Test Plan

Before this could be tested, we would need to make one change that wasn't apparent to me when I 
started on this. We would probably shift the logic around authenticating and selecting the repo up
to the root level, as opposed to the task level. This would let us specify different repositories
for testing.

For testing this script, I would break the tests down by component and primarily test them from the
end user's perspective rather than going overboard on unit tests. To do this, we could have
several test fixtures, each of which would be a Github repository set up in a specific way. These
test fixtures could exist in perpetuity or they could be automatically stood up as part of test
setup using the Github API.

Some specific test cases I would handle, by task:

## "Core" Tests or Tests For All Tasks

- Test that we can determine the current release from the release.plist file.
- Test that an error is raised if the current release is not in the master release_info.csv file.
- Test we can parse releases from the release_info.csv file.
  - Ensure we ignore empty lines
  - Ensure we discard records with too many lines
  - Ensure we discard records where the version is formatted incorrectly
- Test that an error is raised if the GITHUB_ACCESS_TOKEN environment variable isn't set.
- Test that an error is raised if a module in the tasks/ folder is malformed.
- Test that only the tasks specified with the --tasks parameter are run.

## Tests for Creating a Release Branch

- Test that an error is raised if the release branch we want to create already exists.
- Test that a new release branch with the correct name exists after the task is run.
- Test that the new release branch is based off of the right commit.

## Tests for Generating a Feature Flag Report

- Test that if there is no previous version in the release_info.csv file, then the current flag data
  is output instead.
- Test that if there is no previous branch in the Github repository, then the current flag data
  is output instead.
- Test that the feature flag report can handle feature flags that exist in the current release but
  not in the previous release.
- Test that the feature flag report can handle feature flags that exist in the previous release but
  not in the current release.
- Test that the out_flags.csv file is generated correctly after the task is run.

## Tests for Updating the PList File

- Test that an error is generated if there is is no next release in the release_info.csv file.
- Test that a commit is created for the release.plist file in the Github repo and that it has the
  correct values.

# Future Enhancements

These are a couple things I thought about doing but decided were overkill for the assignment

## Argparse Subparsers

Each task could implement its own ArgumentParser, which would be returned by a get_args_parser() method, ie:

```python
class Task():
    def get_arg_parser() -> argparse.ArgumentParser:
        pass
```

This would allow you to specify command like arguments that are only applicable to a single task. If you wanted to run the "create_release_branch" task against a different repository - for testing, for instance - you could do something like this:

```bash
python3 release.py create-release-branch --repo-url=https://alternate-url-to-url
```

## Rollback Logic

If part of an operation fails, it's always nice if the script rolls back the parts that it wasn't able to complete.

For example, if the increment_plist task doesn't successfully commit the plist after the fact, then the release.plist file should be restored to its original state so it doesn't get re-incremented on second run.

## Requirements Preflight

Each task could potentially have a check_requirements function that would perform some basic checks
to make sure that the task could be run before allowing a user to run it. This would ensure that,
for example, the user at least has their github access token setup before they try to run the
script. Some examples:

- release.plist exists
- github access token setup
- has the correct pip packages installed if one task requires specialized ones
