import csv
import logging
import plistlib
from abc import ABCMeta
from collections import namedtuple
from os import path, getcwd

# probably better to parse these from the github repo vs local repo in the future
#
CURRENT_RELEASE_FILENAME = path.join(getcwd(), "release.plist")
AVAILABLE_RELEASES_FILENAME = path.join(getcwd(), "releng", "release_info.csv")
REPOSITORY_NAME = "bfuoco/br-code-exercise-172579038"

Release = namedtuple('Release', 'version name')


class TaskState:
    """Encapsulates the general state of the task runner.

    This object is created by the task runner harness and is propagated to each task. It contains
    state information common to all tasks, such as the current release and available releases.

    In the future, this could be used to store task-specific state, which could be used for
    rollback operations.
    """
    def __init__(
            self,
            root_logger: logging.Logger,
            current_release: Release,
            available_releases: dict[str ,str]):
        self.root_logger = root_logger
        self.current_release = current_release
        self.available_releases = available_releases

    def next_release(self) -> Release:
        """Returns the next release.

        The next release will beselected from the available releases. It will be the release with
        the lowest version number that is also higher than the current release's version number.
        """
        log = self.root_logger
        cur_version, cur_name = self.current_release

        if not cur_version in self.available_releases:
            raise RuntimeError(
                f"can't determine next version: current version {cur_version} does not appear in "\
                f"the list of available releases")
        elif self.available_releases[cur_version] != cur_name:
            log.warning(
                f"current version {cur_version} appears in the list of available releases, but "\
                f"has a different name: {self.available_releases[cur_version]}")

        next_version = None
        for version, version_name in self.available_releases.items():
            if semver_compare(version, cur_version) == 1:
                if next_version is None or semver_compare(version, next_version) == -1:
                    next_version = version

        if next_version is None:
            raise RuntimeError(
                f"can't determine next version: no version after {cur_version} is available in "\
                f"the available releases file")

        return Release(next_version, self.available_releases[next_version])

    def previous_release(self) -> Release:
        """Returns the previous release.

        The previous release will beselected from the available releases. It will be release with
        the highest version number that is also lower than the current release's version number.
        """
        log = self.root_logger
        cur_version, cur_name = self.current_release

        if not cur_version in self.available_releases:
            raise RuntimeError(
                f"can't determine previous version: current version {cur_version} does not appear "\
                f"in the list of available releases")
        elif self.available_releases[cur_version] != cur_name:
            log.warning(
                f"current version {cur_version} appears in the list of available releases, but "\
                f"has a different name: {self.available_releases[cur_version]}")

        prev_version = None
        for version, version_name in self.available_releases.items():
            if semver_compare(version, cur_version) == -1:
                if prev_version is None or semver_compare(version, prev_version) == 1:
                    prev_version = version

        if prev_version is None:
            raise RuntimeError(
                f"can't determine previous version: no version before {cur_version} is available "\
                f"in the available releases file")

        return Release(prev_version, self.available_releases[prev_version])


class Task(metaclass=ABCMeta):
    """Defines an abstract class for a base class object.

    Uses the abstract base class library to ensure that release task classes implement the required
    methods. The __subclasshook__ method is executed when issubclass compares release task instances
    to this abstract base class. If it returns true, then the release task class is valid.

    The validation was implemented this way to facilitate some level of re-use without tying
    ourselves to a specific base class contract. Because we only have three tasks, we don't want
    to arbitrarily limit how we can develop future tasks without having a better understanding of
    what those requirements might be.
    
    In the future, it may make more sense to have the release task classes derive from a base class
    instead.

    See https://docs.python.org/3/library/abc.html for more information.
    """
    @classmethod
    def __subclasshook__(cls, subclass):
        required_functions = set([
            "run"])
        
        # __mro__ is the chain of derived classes for a subclass.
        #
        # we check here to see if any definition has all of the required methods by comparing each
        # base class's set of method names to the set of required function names for our tasks.
        #
        return any(required_functions.issubset(set(definition.__dict__)) for definition in subclass.__mro__)


class TaskDef:
    """A dummy class for type hinting.
    """
    def run(state: TaskState) -> None:
        pass


def get_current_release() -> Release:
    log = logging.getLogger("release")
    log.debug(f"parsing current version information from {CURRENT_RELEASE_FILENAME}")

    with open(CURRENT_RELEASE_FILENAME, "r", encoding="utf-8") as current_release_file:
        # instead of loading directly from the file pointer, we load it as text content, strip
        # the whitespace, adn then re-encode it as bytes.
        #
        # plistlib will fail if there is whitespace at the beginning of the plist file, so this
        # is a less brittle and accounts for times when people may be editing the file by
        # hand.
        current_release_content = current_release_file.read().strip()

    plist = plistlib.loads(current_release_content.encode("utf-8"), fmt=plistlib.FMT_XML)

    version = plist['CFBundleShortVersionString'].strip()
    name = plist['SLKReleaseName'].strip()
 
    log.debug(f"current release version is {name}/{version}")

    return Release(version, name)


def get_available_releases() -> dict[str, str]:
    """Parses the release information file to get information on which releases are available.

    This is used when determining which release is the "next" or "previous" release.
    """
    log = logging.getLogger("release")
    log.debug(f"parsing available releases from {AVAILABLE_RELEASES_FILENAME}")

    # the assumption here is that each version and name must be unique, so these sets are used
    # to ensure this.
    #
    name_set = set()
    version_set = set()
    available_releases = dict()

    # this loop is mostly about filtering out unusable data. specifically, we ignore:
    #
    #   - empty lines
    #   - any line with more than 2 "columns"
    #   - any line where one or more columns is empty
    #   - any name/version value that is duplicated
    #
    # if I could do this again, I would have probably just used the csv.DictReader class.
    #
    with open(AVAILABLE_RELEASES_FILENAME, "r", encoding="utf-8") as available_releases_file:
        release_reader = csv.reader(available_releases_file, delimiter=',')

        for i, release in enumerate(release_reader):
            line_number = i + 1

            if (column_count := len(release)) == 0:
                log.debug(f"ignoring line {line_number}; empty line")
                continue
            elif column_count != 2:
                log.debug(f"ignoring line {line_number}; expected 2 values, got {column_count}: {release}")
                continue

            name = release[0].strip()
            version = release[1].strip()

            if len(name) == 0 or len(version) == 0:
                log.debug(f"ignoring line {line_number}; name and version cannot be empty: {release}")
                continue

            if not is_semver(version):
                # ignore the initial heading but generate a warning if invalid semver number
                # is encountered on subsequent lines
                #
                if line_number > 0:
                    log.debug(f"ignoring line {line_number}; version is invalid: {version}")
                continue

            if name in name_set:
                log.debug(f"ignoring line {line_number}; duplicate release name: {name}")
                continue
            name_set.add(name)

            if version in version_set:
                log.debug(f"ignoring line {line_number}; duplicate release version: {version}")
                continue
            version_set.add(name)

            available_releases[version] = name

            log.debug(f"found version {name}/{version}")

    return available_releases


# there is a good semver package available and i would have preferred to use it, but it is
# strict on what it accepts.
#
# unfortunately, our versions do not have a patch version, and cannot be processed by the
# python-semver module.
#
# rather than coerce our versions into an acceptable format, it seemed easier to write a couple
# utility functions to handle this for now
#


def is_semver(version: str) -> bool:
    """Determines whether or not a value is valid semver (or semver-ish).

    Returns True if the value consists only of integers separated by a dot and False if the value
    is anything else.
    """
    return all(n.isnumeric() for n in version.split('.'))


def semver_compare(version1: str, version2: str) -> int:
    """Compares two semver-ish values.

    This function does not check if the values are in the correct format before comparing them.
    
    Returns -1 if version1 is smaller than version2.
    Returns  0 if version1 is equal to version2.
    Returns  1 if version1 is larger than version2.
    """
    version1_parts = version1.split('.')
    version2_parts = version2.split('.')

    # handles comparisons like 3.7.0 to 3.7, which if the zero isn't popped will consider the values
    # to not be equivalent
    #
    while version1_parts[-1] == 0:
        version1_parts.pop()
    while version2_parts[-1] == 0:
        version2_parts.pop()

    if version1_parts < version2_parts:
        return -1
    elif version1_parts > version2_parts:
        return 1
    else:
        return 0
