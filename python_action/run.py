"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API. If executed from command-line, then [`main()`][python_action.run.main] is
the entrypoint.

.. seealso::
    - `github rest API reference for pulls <https://docs.github.com/en/rest/reference
      /pulls>`_
    - `github rest API reference for repos <https://docs.github.com/en/rest/reference
      /repos>`_
    - `github rest API reference for issues <https://docs.github.com/en/rest/reference
      /issues>`_
"""
import os
import sys
import re
import argparse
import json
import requests
from . import (
    Globals,
    GlobalParser,
    logger,
    log_response_msg,
)
from .parse_pylint import annotate_pylint_note, run_pylint


# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/check-python-sources")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "push")
GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL", "https://github.com")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "0")
GITHUB_SHA = os.getenv("GITHUB_SHA", "562351563de8d47627ce5cfbd695ba0953aefd93")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", None))
API_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.json",
}

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(
    description=__doc__[: __doc__.find("If executed from")]
)
cli_arg_parser.add_argument(
    "--verbosity",
    default="10",
    help="The logging level. Defaults to level 20 (aka 'logging.INFO').",
)
cli_arg_parser.add_argument(
    "--extensions",
    default="py,pyi,toml",
    help="The file extensions to run the action against. This comma-separated string "
    "defaults to 'py,pyi,toml'.",
)
cli_arg_parser.add_argument(
    "--repo-root",
    default=".",
    help="The relative path to the repository root directory. The default value '.' is "
    "relative to the runner's GITHUB_WORKSPACE environment variable.",
)
cli_arg_parser.add_argument(
    "--diff-only",
    default="false",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'true' to only analyse changes in the event's diff. "
    "Defaults to 'false'.",
)


def set_exit_code(override: int = None) -> int:
    """Set the action's exit code.

    :param int override: The number to use when overriding the action's logic.

    Returns:
        The exit code that was used. If the ``override`` parameter was not passed,
        then this `int` value will describe (like a bool value) if any checks failed.
    """
    exit_code = override if override is not None else bool(GlobalParser.pylint_notes)
    print(f"::set-output name=checks-failed::{exit_code}")
    return exit_code


def get_list_of_changed_files() -> None:
    """Fetch the JSON payload of the event's changed files. Sets the
    :attr:`~python_action.__init__.Globals.FILES` attribute."""
    logger.info("processing %s event", GITHUB_EVENT_NAME)
    with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
        Globals.EVENT_PAYLOAD = json.load(payload)
        logger.debug(json.dumps(Globals.EVENT_PAYLOAD))

    files_link = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "push":
        files_link += f"commits/{GITHUB_SHA}"
    else:
        logger.warning("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    logger.info("Fetching files list from url: %s", files_link)
    Globals.response_buffer = requests.get(files_link)
    temp_json = Globals.response_buffer.json()
    Globals.FILES = temp_json["files"]
    logger.debug("files json:\n%s", json.dumps(Globals.FILES, indent=2))


def filter_out_non_source_files(ext_list: str, diff_only: bool) -> None:
    """Exclude undesired files (specified by user input 'extensions'). This filter
    applies to the event's :attr:`~python_action.__init__.Globals.FILES` attribute.

    :param str ext_list: A comma-separated `str` of extensions that are concerned.
    :param bool diff_only: A flag that forces focus on only changes in the event's diff
        info.

    .. note::
        This will exit early when nothing left to do.
    """
    ext_list = ext_list.split(",")
    files = []
    for file in Globals.FILES:
        extension = re.search("\.\w+$", file["filename"])
        if (
            extension is not None
            and extension.group(0)[1:] in ext_list
            and not file["status"].endswith("removed")
        ):
            if diff_only and "patch" in file.keys():
                # get diff details for the file's changes
                line_filter = []
                file["diff_line_map"], line_numb_in_diff = ({}, 0)
                # diff_line_map is a dict for which each
                #     - key is the line number in the file
                #     - value is the line's "position" in the diff
                for i, line in enumerate(file["patch"].splitlines()):
                    if line.startswith("@@ -"):
                        changed_hunk = line[line.find(" +") + 2 : line.find(" @@")]
                        changed_hunk = changed_hunk.split(",")
                        start_line = int(changed_hunk[0])
                        hunk_length = int(changed_hunk[1])
                        line_filter.append([start_line, hunk_length + start_line])
                        line_numb_in_diff = start_line
                    elif not line.startswith("-"):
                        file["diff_line_map"][line_numb_in_diff] = i
                        line_filter[-1][1] = line_numb_in_diff
                        line_numb_in_diff += 1
                file["line_filter"] = line_filter
            elif diff_only:
                continue
            files.append(file)

    if not files:
        # exit early if no changed files are source files
        logger.info("No source files need checking!")
        sys.exit(set_exit_code(0))
    else:
        logger.info("File names:\n\t%s", "\n\t".join([f["filename"] for f in files]))
        Globals.FILES = files
        with open(".changed_files.json", "w", encoding="utf-8") as temp:
            json.dump(Globals.FILES, temp, indent=2)


def verify_files_are_present() -> None:
    """Download the files if not present.

    .. hint::
        This function assumes the working directory is the root of the invoking
        repository. If files are not found, then they are downloaded to the working
        directory. This may be bad for files with the same name from different folders.
    """
    for file in Globals.FILES:
        file_name = file["filename"].replace("/", os.sep)
        if not os.path.exists(file_name):
            logger.info("Downloading file from url: %s", file["raw_url"])
            download = requests.get(file["raw_url"])
            with open(os.path.split(file_name)[1], "w", encoding="utf-8") as temp:
                temp.write(download)


def capture_linters_output(diff_only: bool):
    """Execute and capture all output from clang-tidy and clang-format. This aggregates
    results in the :attr:`~python_action.__init__.Globals.OUTPUT`.

    :param bool diff_only: A flag that forces focus on only changes in the event's diff
        info.
    """
    if GITHUB_EVENT_NAME == "push":
        diff_only = False  # diff comments are not supported for push events
    for file in Globals.FILES:
        filename = file["filename"]
        if not os.path.exists(file["filename"]):
            filename = os.path.split(file["raw_url"])[1]
        logger.info("Performing checkup on %s", filename)

        run_pylint(filename, file, diff_only)


def post_results():
    """Post action's results using REST API."""
    if GITHUB_TOKEN is None:
        logger.error("The GITHUB_TOKEN is required!")
        sys.exit(set_exit_code(1))

    url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    logger.info("checks URL: %s", url + f"commits/{GITHUB_SHA}/" + "check-runs")
    url += "check-runs"
    data = {
        "name": "check-python-sources",
        "head_sha": GITHUB_SHA,
        "details_url": f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}",
        "external_id": os.getenv("GITHUB_ACTION", 0),
        "conclusion": "completed",  # not required if we don't timestamp the run
        "output": [],
    }

    annotations = []
    for result in GlobalParser.pylint_notes:
        for note in result:
            annotations.append(annotate_pylint_note(note))

    index = 0
    while 0 <= index < len(annotations):
        data["output"] = annotations[index:50]
        check_run_id, method = (0, "POST")
        if 100 > index >= 50:
            data["check_run_id"] = check_run_id
            method = "PATCH"
            url += str(check_run_id)
        logger.debug("payload: %s", json.dumps(data, indent=2))
        Globals.response_buffer = requests.request(
            method=method,
            url=url,
            headers=API_HEADERS,
            data=data,
        )
        index += 50
        json_response = json.loads(Globals.response_buffer.text)
        if "id" in json_response.keys():
            check_run_id = json_response["id"]
        logger.info(
            "Got %d from %sing a checks run %d",
            Globals.response_buffer.status_code,
            "creat" if index < 50 else "updat",
            check_run_id,
        )
        log_response_msg(True)

    set_exit_code(1 if annotations else 0)


def main():
    """The main script."""

    # The parsed CLI args
    args = cli_arg_parser.parse_args()

    # set logging verbosity
    logger.setLevel(int(args.verbosity))

    # change working directory
    os.chdir(args.repo_root)

    get_list_of_changed_files()
    filter_out_non_source_files(args.extensions, args.diff_only)
    verify_files_are_present()
    capture_linters_output(args.diff_only)
    post_results()


if __name__ == "__main__":
    main()
