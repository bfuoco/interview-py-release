import csv
import os
from ..core import TaskState, REPOSITORY_NAME
from github import Github, GithubException

class Task:
    def run(state: TaskState) -> None:
        log = state.root_logger.getChild("generate-feature-report")

        log.info(f"generating a feature flag change report")
        log.info(f"current release is {state.current_release.name}/{state.current_release.version}")

        access_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if access_token is None:
            raise RuntimeError("The GITHUB_ACCESS_TOKEN environment variable must contain a valid Github access token,")

        g = Github(access_token)
        repo = g.get_repo(REPOSITORY_NAME)

        # we'll try to build out dictionaries of both current and previous features. if we can't
        # parse the previous features because - for example - a branch doesn't exist, we'll only
        # display the current features
        #
        features = dict()
        prev_features = dict()

        # unhardcode this at some point
        #
        features_file = repo.get_contents("featureflags/FF.csv", ref="master")
        features_lines = features_file.decoded_content.decode("utf-8").split("\n")

        features_reader = csv.DictReader(features_lines, fieldnames=("name","state"))
        for row in features_reader:
            # cleaning the names a bit so we can compare properly to the previous csv's keys
            #
            name = row["name"].strip().upper()
            feature_state = row["state"].strip().upper()

            if feature_state not in set(["ON", "OFF"]):
                log.warning(f"unknown value for feature flag {name}")
                continue

            features[name] = feature_state

        skip_previous = False
        try:
            previous_release = state.previous_release()
            log.info(f"previous release is {previous_release.name}/{previous_release.version}")
        except Exception as err:
            log.warning(f"could not parse previous release from available releases file: {err}")
            skip_previous = True

        if not skip_previous:
            try:
                features_file = repo.get_contents("featureflags/FF.csv", ref=f"{previous_release.name}/{previous_release.version}")
                features_lines = features_file.decoded_content.decode("utf-8").split("\n")

                features_reader = csv.DictReader(features_lines, fieldnames=("name","state"))
                for row in features_reader:
                    name = row["name"].strip().upper()
                    feature_state = row["state"].strip().upper()
                    
                    if feature_state not in set(["ON", "OFF"]):
                        log.warning(f"unknown value for feature flag {name}")
                        continue

                    prev_features[name] = feature_state
            except GithubException as err:
                log.warning(f"no previous feature flag data could be read from branch {previous_release.name}/{previous_release.version}")

        prev_features['FLAG_Z'] = 'ON'

        # accounting for the case where flags may be added or removed
        #
        flag_names = set(features.keys()).union(prev_features.keys())
        flag_names = list(flag_names)
        flag_names.sort()

        report_contents = "flag_name,current_version,previous_version\n"

        log.info("feature flag report")
        log.info("flag\tcur\tprev")
        log.info("-----------------------")

        for name in flag_names:
            current_value = features.get(name) or "-"
            prev_value = prev_features.get(name) or "-"

            log.info(f"{name}\t{current_value}\t{prev_value}") 
            report_contents += f"{name},{current_value},{prev_value}\n"

        output_file = "out_flags.csv"
        log.info(f"outputting to {output_file}")

        with open(output_file, "w") as out_flags_files:
            out_flags_files.write(report_contents)
        
        log.info("feature flag report has been generated")

