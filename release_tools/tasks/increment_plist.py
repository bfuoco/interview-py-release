import os
import plistlib
from ..core import TaskState, CURRENT_RELEASE_FILENAME, REPOSITORY_NAME
from github import Github, GithubException

class Task:
    def run(state: TaskState) -> None:
        log = state.root_logger.getChild("increment-plist")

        log.info(f"incrementing version in the current release plist file at {CURRENT_RELEASE_FILENAME}")
        log.info(f"current release is {state.current_release.name}/{state.current_release.version}")

        next_release = state.next_release()

        log.info(f"next release is {next_release.name}/{next_release.version}")

        with open(CURRENT_RELEASE_FILENAME, "r", encoding="utf-8") as current_release_file:
            # see core.py for why we load it like this, the tldr is to account for unexpected
            # whitespace issues
            #
            current_release_content = current_release_file.read().strip()
            plist = plistlib.loads(current_release_content.encode("utf-8"), fmt=plistlib.FMT_XML)

        plist['SLKReleaseName'] = next_release.name
        plist['CFBundleShortVersionString'] = next_release.version

        with open(CURRENT_RELEASE_FILENAME, "wb") as current_release_file:
            plistlib.dump(plist, current_release_file, fmt=plistlib.FMT_XML, sort_keys=False)

        log.info(f"the current release plist file has been updated with the next release version")

        access_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if access_token is None:
            raise RuntimeError("The GITHUB_ACCESS_TOKEN environment variable must contain a valid Github access token,")

        g = Github(access_token)
        repo = g.get_repo(REPOSITORY_NAME)

        with open(CURRENT_RELEASE_FILENAME, "rb") as current_release_file:
            current_release_content = current_release_file.read()

        # unhardcode this at some point
        #
        github_file = repo.get_contents("release.plist")

        repo.update_file(
            path=github_file.path, 
            message=f"Update current release to {next_release.name}/{next_release.version}",
            content=current_release_content,
            sha=github_file.sha)

        log.info("new release file has been committed")
