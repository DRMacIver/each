import os

from each.each import LineWorkItem


def test_creates_pipe():
    """as_input_file returns a file descriptor from which we can read the original line."""
    line = "foo"
    item = LineWorkItem(name="foo", line=line)
    fd = item.as_input_file()
    output_line = os.read(fd, len(line) + 1).decode("utf-8")
    assert output_line == line + "\n"
