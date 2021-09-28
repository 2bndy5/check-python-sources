"""Parse output from clang-tidy's stdout"""
import os
import sys
import re
import subprocess
import json
from . import GlobalParser, logger


def annotate_pylint_note(obj: dict) -> str:
    """Translate a 1 notification from pylint to github's checks API.

    :param dict obj: The JSON object output by pylint (for 1 notification).
        A typical JSON object output from pylint looks like:

        .. code-block:: json

            {
                "type": "error",
                "module": "basic_test",
                "obj": "",
                "line": 3,
                "column": 19,
                "path": "tests/basic_test.py",
                "symbol": "syntax-error",
                "message": "invalid syntax (<unknown>, line 3)",
                "message-id": "E0001"
            }

    :Returns:
        A serialized JSON object (`str`) that can be used by github's checks API.
    """
    priority = {
        "convention": "notice",
        "refactor": "notice",
        "warning": "warning",
        "error": "failure",
        "fatal": "failure",
    }
    return json.dumps(
        {
            "path": obj["path"],
            "start_line": obj["line"],
            "end_line": obj["line"],
            "start_column": obj["column"],
            "end_column": obj["column"],
            "annotation_level": priority[obj["type"]],
            "message": obj["message"],
            "title": obj["symbol"] + " [" + obj["message-id"] + "]",
        }
    )


def run_pylint(filename: str, file_info: dict, diff_only: bool) -> None:
    """Run a pylint on a given (single) file.

    :param str filename: The path and name of the file to be checked.
    :param dict file_info: A JSON type `dict` containing info about the given file.
        This info is augmented from the REST API's list of changed files, and it is
        only used when the github action's (or CLI argument) ``--diff-only`` option is
        asserted.
    """
    cmds = ["pylint", "--output-format=json", "--exit-zero"]
    if "line_filter" not in file_info.keys():
        cmds.append(filename)
    else:
        # get source code from file, & pass it to the tool via stdin
        for lines in file_info["line_filter"]:
            cmds.append(lines)
    result = subprocess.run(cmds, check=True, capture_output=True)
    output = json.loads(result.stdout)
    logger.debug(json.dumps(output, indent=2))
    GlobalParser.pylint_notes.append(output)


if __name__ == "__main__":
    logger.setLevel(10)
    run_pylint("tests/basic_test.py", {}, False)
    for result in GlobalParser.pylint_notes:
        for note in result:
            logger.info(annotate_pylint_note(note))
