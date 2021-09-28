"""The Base module of the :mod:`python_action` package. This holds the objects shared by
multiple modules."""
import io
import os
import logging

FOUND_RICH_LIB = False
try:
    from rich.logging import RichHandler

    FOUND_RICH_LIB = True

    logging.basicConfig(
        format="%(name)s: %(message)s",
        handlers=[RichHandler(show_time=False)],
    )

except ImportError:
    logging.basicConfig()

#: The logging.Logger object used for outputing data.
logger = logging.getLogger("Python-Checker")
if not FOUND_RICH_LIB:
    logger.debug("rich module not found")


class Globals:
    """Global variables for re-use (non-constant)."""

    FILES = []
    """The reponding payload containing info about changed files."""
    EVENT_PAYLOAD = {}
    """The parsed JSON of the event payload."""
    response_buffer = None
    """A shared response object for `requests` module."""


class GlobalParser:
    """Global variables specific to output parsers. Each element in each of the
    following attributes represents a clang-tool's output for 1 source file.
    """

    pylint_notes = []
    """This can only be a `list` of JSON-type `dict` (generated by pylint)"""
    black_advice = []
    """This can only be a `list` of type ??? (not implemented yet)"""


def get_lines_from_file(file_path: str) -> list:
    """Get all the lines from a file as a list of strings.

    :param str file_path: The path to the file.
    :Returns: A list of lines (each a `str`).
    """
    with open(file_path, encoding="utf-8") as temp:
        return temp.readlines()


def get_line_cnt_from_cols(file_path: str, offset: int) -> tuple:
    """Gets a line count and columns offset from a file's absolute offset.

    :param str file_path: Path to file.
    :param int offset: The byte offset to translate

    Returns:
        A `tuple` of 2 `int` numbers:

        - Index 0 is the line number for the given offset.
        - Index 1 is the column number for the given offset on the line.
    """
    line_cnt = 1
    last_lf_pos = 0
    cols = 1
    file_path = file_path.replace("/", os.sep)
    with io.open(file_path, "r", encoding="utf-8", newline="\n") as src_file:
        src_file.seek(0, io.SEEK_END)
        max_len = src_file.tell()
        src_file.seek(0, io.SEEK_SET)
        while src_file.tell() != offset and src_file.tell() < max_len:
            char = src_file.read(1)
            if char == "\n":
                line_cnt += 1
                last_lf_pos = src_file.tell() - 1  # -1 because LF is part of offset
                if last_lf_pos + 1 > max_len:
                    src_file.newlines = "\r\n"
                    src_file.seek(0, io.SEEK_SET)
                    line_cnt = 1
        cols = src_file.tell() - last_lf_pos
    return (line_cnt, cols)


def log_response_msg(override: bool = False):
    """Output the response buffer's message on failed request.

    :param bool override: Force this function to always output the body of the
        :attr:`~Globals.response_buffer` (even if response's status code is less than 400).
    """
    if Globals.response_buffer.status_code >= 400 or override:
        logger.error("response returned message: %s", Globals.response_buffer.text)
