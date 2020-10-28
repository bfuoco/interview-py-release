import os
from ..core import TaskState, REPOSITORY_NAME
from github import Github, GithubException

class Task:
    def run(state: TaskState) -> None:
        log = state.root_logger.getChild("create-release-branch")

        log.info(f"creating a new release branch from master")
        log.info(f"current release is {state.current_release.name}/{state.current_release.version}")

        if "GITHUB_ACCESS_TOKEN" not in os.environ:
            raise RuntimeError(
                "you must create an access token and assign it to the the GITHUB_ACCESS_TOKEN "\
                "environment variable")

        access_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if access_token is None:
            raise RuntimeError("The GITHUB_ACCESS_TOKEN environment variable must contain a valid Github access token,")

        branch_name = f"{state.current_release.name}/{state.current_release.version}"
        log.info(f"branch {branch_name} will be created in repository {REPOSITORY_NAME}")

        g = Github(access_token)
        repo = g.get_repo(REPOSITORY_NAME)

        # this is more about grabbing the master branch commit than confirming it exists.
        #
        try:
            master_branch = repo.get_branch("master")
            log.info(f"master branch is at commit {master_branch.commit}")
        except GithubException:
            log.error("could not retrieve the master branch, does it exist?")
            raise

        try:
            repo.get_branch(branch_name)
            raise RuntimeError(f"Could not create new branch {branch_name}, branch already exists")
        except GithubException:
            log.info(f"okay to create {branch_name}, branch does not exist")
            pass

        new_branch_ref = repo.create_git_ref(f"refs/heads/{branch_name}", master_branch.commit.sha)

        log.info(f"created new branch: {branch_name}")
