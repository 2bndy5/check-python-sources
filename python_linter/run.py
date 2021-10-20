"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API. If executed from command-line, then [`main()`][python_linter.run.main] is
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
import configparser
import argparse
import json
import requests
from . import (
    Globals,
    GlobalParser,
    logger,
    logging,
    log_commander,
    start_log_group,
    end_log_group,
)
from .parse_pylint import annotate_pylint_note, run_pylint


# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/check-python-sources")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "push")
GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL", "https://github.com")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "0")
GITHUB_SHA = os.getenv("GITHUB_SHA", "b4a3ded3367cc2a7346ab74e4452bf1b51f8420f")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", ""))
API_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.json",
}

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(
    description=__doc__[: __doc__.find("If executed from")]
)
cli_arg_parser.add_argument(
    "-v",
    "--verbosity",
    default="10",
    help="The logging level. Defaults to level 20 (aka 'logging.INFO').",
)
cli_arg_parser.add_argument(
    "-e",
    "--extensions",
    default="py,pyi",
    help="The file extensions to run the action against. This comma-separated string "
    "defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "-r",
    "--repo-root",
    default=".",
    help="The relative path to the repository root directory. The default value "
    "'%(default)s' is relative to the runner's GITHUB_WORKSPACE environment variable.",
)
cli_arg_parser.add_argument(
    "-i",
    "--ignore",
    nargs="?",
    help="Set this option with paths to ignore. In the case of multiple "
    "paths, you can the pipe character ('|') between each path. This can "
    "also have files, but the file's relative path has to be specified as well "
    "with the filename. Prefix any path with a bang ('!') to explicitly include it.",
)
cli_arg_parser.add_argument(
    "--lines-changed-only",
    default="false",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'true' to only analyse changes in the event's diff. "
    "Defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "--files-changed-only",
    default="true",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'false' to analyse any source files in the repo. "
    "Defaults to %(default)s.",
)


def is_file_in_list(paths: list, file_name: str, prompt: str) -> bool:
    """Detirmine if a file is specified in a list of paths and/or filenames.

    :param list paths: A list of specified paths to compare with. This list can contain
        a specified file, but the file's path must be included as part of the filename.
    :param str file_name: The file's path & name being sought in the ``paths`` list.
    :param str prompt: A debugging prompt to use when the path is found in the list.
    :Returns:
        - True if ``file_name`` is in the ``paths`` list.
        - False if ``file_name`` is not in the ``paths`` list.
    """
    for path in paths:
        result = os.path.commonpath([path, file_name]).replace(os.sep, "/")
        if result == path:
            logger.debug(
                '"./%s" is %s as specified in the domain "./%s"',
                file_name,
                prompt,
                path,
            )
            return True
    return False


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
    :attr:`~python_linter.__init__.Globals.FILES` attribute."""
    start_log_group("Get list of specified source files")
    files_link = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        files_link += f"pulls/{Globals.EVENT_PAYLOAD['number']}/files"
    elif GITHUB_EVENT_NAME == "push":
        files_link += f"commits/{GITHUB_SHA}"
    else:
        logger.warning("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    logger.info("Fetching files list from url: %s", files_link)
    Globals.FILES = requests.get(files_link).json()


def filter_out_non_source_files(
    ext_list: list, ignored: list, not_ignored: list, lines_changed_only: bool
) -> bool:
    """Exclude undesired files (specified by user input 'extensions'). This filter
    applies to the event's :attr:`~python_linter.__init__.Globals.FILES` attribute.

    :param list ext_list: A `list` of file extensions that should be attended.
    :param list ignored_paths: A list of paths to explicitly ignore.
    :param list not_ignored: A list of paths to explicitly not ignore.
    :param bool lines_changed_only: A flag that forces focus on only changes in the
        event's diff info.

    :Returns:
        True if there are files to check. False will invoke a early exit (in
        `main()` when no files to be checked.
    """
    files = []
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        if (
            os.path.splitext(file["filename"])[1][1:] in ext_list
            and not file["status"].endswith("removed")
            and (
                not is_file_in_list(ignored, file["filename"], "ignored")
                or is_file_in_list(not_ignored, file["filename"], "not ignored")
            )
        ):
            if lines_changed_only and "patch" in file.keys():
                # get diff details for the file's changes
                line_filter = {
                    "name": file["filename"].replace("/", os.sep),
                    "lines": [],
                }
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
                        line_filter["lines"].append(
                            [start_line, hunk_length + start_line]
                        )
                        line_numb_in_diff = start_line
                    elif not line.startswith("-"):
                        file["diff_line_map"][line_numb_in_diff] = i
                        line_filter["lines"][-1][1] = line_numb_in_diff
                        line_numb_in_diff += 1
                file["line_filter"] = line_filter
            elif lines_changed_only:
                continue
            files.append(file)

    if files:
        logger.info(
            "Giving attention to the following files:\n\t%s",
            "\n\t".join([f["filename"] for f in files]),
        )
        if GITHUB_EVENT_NAME == "pull_request":
            Globals.FILES = files
        else:
            Globals.FILES["files"] = files
        if not os.getenv("CI"):  # if not executed on a github runner
            with open(".changed_files.json", "w", encoding="utf-8") as temp:
                # dump altered json of changed files
                json.dump(Globals.FILES, temp, indent=2)
    else:
        logger.info("No source files need checking!")
        return False
    return True


def verify_files_are_present() -> None:
    """Download the files if not present.

    .. hint::
        This function assumes the working directory is the root of the invoking
        repository. If files are not found, then they are downloaded to the working
        directory. This may be bad for files with the same name from different folders.
    """
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        file_name = file["filename"].replace("/", os.sep)
        if not os.path.exists(file_name):
            logger.info("Downloading file from url: %s", file["raw_url"])
            download = requests.get(file["raw_url"])
            with open(os.path.split(file_name)[1], "w", encoding="utf-8") as temp:
                temp.write(download.text)


def list_source_files(ext_list: list, ignored_paths: list, not_ignored: list) -> bool:
    """Make a list of source files to be checked. The resulting list is stored in
    [`FILES`][Global.FILES].

    :param list ext_list: A `list` of file extensions that should be attended.
    :param list ignored_paths: A list of paths to explicitly ignore.
    :param list not_ignored: A list of paths to explicitly not ignore.

    :Returns:
        True if there are files to check. False will invoke a early exit (in
        [`main()`][python_linter.run.main()]) when no files to be checked.
    """
    start_log_group("Get list of specified source files")
    if os.path.exists(".gitmodules"):
        submodules = configparser.ConfigParser()
        submodules.read(".gitmodules")
        for module in submodules.sections():
            logger.info(
                "Apending submodule to ignored paths: %s", submodules[module]["path"]
            )
            ignored_paths.append(submodules[module]["path"])

    root_path = os.getcwd()
    for dirpath, _, filenames in os.walk(root_path):
        path = dirpath.replace(root_path, "").lstrip(os.sep)
        path_parts = path.split(os.sep)
        is_hidden = False
        for part in path_parts:
            if part.startswith("."):
                # logger.debug("Skipping \".%s%s\"", os.sep, path)
                is_hidden = True
                break
        if is_hidden:
            continue  # skip sources in hidden directories
        logger.debug('Crawling "./%s"', path)
        for file in filenames:
            if os.path.splitext(file)[1][1:] in ext_list:
                file_path = os.path.join(path, file)
                logger.debug('"./%s" is a source code file', file_path)
                if not is_file_in_list(
                    ignored_paths, file_path, "ignored"
                ) or is_file_in_list(not_ignored, file_path, "not ignored"):
                    Globals.FILES.append({"filename": file_path})

    if Globals.FILES:
        logger.info(
            "Giving attention to the following files:\n\t%s",
            "\n\t".join([f["filename"] for f in Globals.FILES]),
        )
    else:
        logger.info("No source files found.")  # this might need to be warning
        return False
    return True


def capture_linters_output() -> None:  # (diff_only: bool) -> None:
    """Execute and capture all output from clang-tidy and clang-format. This aggregates
    results in the :attr:`~python_linter.__init__.Globals.OUTPUT`.

    """
    # :param bool diff_only: A flag that forces focus on only changes in the
    #     event's diff info.
    run_pylint(
        Globals.FILES if isinstance(Globals.FILES, list) else Globals.FILES["files"]
    )


def post_results() -> None:
    """Use github log commands to make annotations from pylint output."""
    # log_commander obj's verbosity is hard-coded to show debug statements
    exit_code = False
    start_log_group("Posting results")
    for result in GlobalParser.pylint_notes:
        exit_code = True
        for note in result:
            log_commander.info(annotate_pylint_note(note))
    end_log_group()
    set_exit_code(1 if exit_code else 0)


def main():
    """The main script."""

    # The parsed CLI args
    args = cli_arg_parser.parse_args()

    # set logging verbosity
    logger.setLevel(int(args.verbosity))

    # change working directory
    os.chdir(args.repo_root)

    # prepare ignored paths list
    ignored, not_ignored = (["__pycache__"], [])  # auto-ignore __pycache__ dir
    if args.ignore is not None:
        args.ignore = args.ignore.split("|")
        for path in args.ignore:
            path = path.lstrip("./")  # relative dir is assumed
            path = path.strip()  # strip leading/trailing spaces
            if path.startswith("!"):
                not_ignored.append(path[1:])
            else:
                ignored.append(path)

    # prepare extensions list
    args.extensions = args.extensions.split(",")

    # change working directory
    os.chdir(args.repo_root)

    if ignored:
        logger.info(
            "Ignoring the following paths/files:\n\t%s",
            "\n\t./".join(f for f in ignored),
        )
    if not_ignored:
        logger.info(
            "Not ignoring the following paths/files:\n\t%s",
            "\n\t./".join(f for f in not_ignored),
        )
    exit_early = False
    if args.files_changed_only:
        # load event's json info about the workflow run
        with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
            Globals.EVENT_PAYLOAD = json.load(payload)
        if logger.getEffectiveLevel() <= logging.DEBUG:
            start_log_group("Event json from the runner")
            logger.debug(json.dumps(Globals.EVENT_PAYLOAD))
            end_log_group()
        get_list_of_changed_files()
        exit_early = not filter_out_non_source_files(
            args.extensions,
            ignored,
            not_ignored,
            args.lines_changed_only if args.files_changed_only else False,
        )
        if not exit_early:
            verify_files_are_present()
    else:
        exit_early = not list_source_files(args.extensions, ignored, not_ignored)
    end_log_group()
    if exit_early:
        sys.exit(set_exit_code(0))

    capture_linters_output()
    post_results()


if __name__ == "__main__":
    main()
