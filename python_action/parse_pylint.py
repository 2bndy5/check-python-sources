"""Parse output from clang-tidy's stdout"""
import subprocess
import json
from . import GlobalParser, logger, log_commander, end_log_group, start_log_group


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
        A `str` that can be used by github's workflow log commands.
    """
    priority = {
        "convention": "notice",
        "refactor": "notice",
        "warning": "warning",
        "error": "error",
        "fatal": "error",
    }
    return (
        "::{level} file={path},line={line},title={path}:{line}:{col} {symbol} [{code}]"
        "::{msg}".format(
            level=priority[obj["type"]],
            path=obj["path"],
            line=obj["line"],
            col=obj["column"],
            symbol=obj["symbol"],
            code=obj["message-id"],
            msg=obj["message"],
        )
    )


def run_pylint(files: list) -> None:
    """Run a pylint on a given (single) file.

    :param list files: A `list` of JSON type `dict` containing info about the given
        files.
    """
    cmds = ["pylint", "--output-format=json", "--exit-zero"]
    for file in files:
        if "line_filter" not in file.keys():
            cmds.append(file['filename'])
        else:  # TODO: line filters not implemented yet (incompatible with pylint)
            # get source code from file, & pass it to the tool via stdin
            for lines in file["line_filter"]:
                cmds.append(lines)
    start_log_group("Performing checkup on files")
    result = subprocess.run(cmds, check=True, capture_output=True)
    output = json.loads(result.stdout)
    GlobalParser.pylint_notes.append(output)
    logger.debug("pylint output:\n%s", json.dumps(output, indent=2))
    if result.returncode:
        logger.error(
            "pylint reported the following errors:\n%s", result.stderr.decode()
        )
    end_log_group()


if __name__ == "__main__":
    logger.setLevel(20)
    run_pylint([{"filename": "tests/basic_test.py"}])
    for pylint_result in GlobalParser.pylint_notes:
        for note in pylint_result:
            log_commander.info(annotate_pylint_note(note))
