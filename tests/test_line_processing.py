import os

import pytest

from each import Each
from each.each import LineWorkItem
from test_main import get_directory_contents


@pytest.mark.parametrize("processes", [1, 2, 4])
@pytest.mark.parametrize("stderr", [False, True])
@pytest.mark.parametrize("stdin", [False, True])
def test_processes_each_line(tmpdir, processes, stderr, stdin):
    input_path = tmpdir.join("input")
    output_path = tmpdir.mkdir("output")
    with input_path.open("w") as input_file:
        for i in range(10):
            input_file.write("hello %d\n" % (i,))

    if stdin:
        if stderr:
            command = "cat >&2"
        else:
            command = "cat"
    else:
        if stderr:
            command = "echo {} | cat >&2"
        else:
            command = "echo {}"

    each = Each(
        command=command,
        source=input_path,
        destination=output_path,
        processes=processes,
        stdin=stdin,
    )
    each.clear_queue()

    output_files = sorted(output_path.listdir())
    assert output_files == [output_path.join("hello %d" % (i,)) for i in range(10)]

    for i, f in enumerate(output_files):
        line = "hello %d" % (i,)
        expected = {"status": "0", "in": line, "out": line, "err": ""}
        if stderr:
            expected.update({"out": "", "err": line})
        assert get_directory_contents(f) == expected


def test_creates_pipe():
    """as_input_file returns a file descriptor from which we can read the original line."""
    line = "foo"
    item = LineWorkItem(name="foo", line=line)
    fd = item.as_input_file()
    output_line = os.read(fd, len(line) + 1).decode("utf-8")
    assert output_line == line + "\n"
