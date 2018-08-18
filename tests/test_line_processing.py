import hashlib
import io
import os
import string

import pytest
from hypothesis import given, strategies as st

from common import gather_output, get_directory_contents
from each import Each, work_items_from_path
from each.each import MAX_NAME_LENGTH, LineWorkItem, work_items_from_file


@pytest.mark.parametrize("processes", [1, 2, 4])
@pytest.mark.parametrize("stderr", [False, True])
@pytest.mark.parametrize("stdin", [False, True])
def test_processes_each_line(tmpdir, processes, stderr, stdin):
    input_path = tmpdir.join("input")
    output_path = tmpdir.mkdir("output")
    lines = ["hello %d" % (i,) for i in range(5)]
    with input_path.open("w") as input_file:
        for line in lines:
            input_file.write(line)
            input_file.write("\n")

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
        work_items=work_items_from_path(input_path),
        destination=output_path,
        processes=processes,
        stdin=stdin,
    )
    each.clear_queue()

    if stderr:
        expected = {line: [{"status": "0", "in": line, "out": "", "err": line}] for line in lines}
    else:
        expected = {line: [{"status": "0", "in": line, "out": line, "err": ""}] for line in lines}
    assert gather_output(output_path) == expected


def test_duplicate_lines(tmpdir):
    """We silently ignore duplicate lines."""
    output_path = tmpdir.mkdir("output")
    line = "hello"

    each = Each(
        command="echo {}",
        work_items=[LineWorkItem(line, line), LineWorkItem(line, line)],
        destination=output_path,
        stdin=False,
    )
    each.clear_queue()

    [output_file] = output_path.listdir()
    expected = {"status": "0", "in": line, "out": line, "err": ""}
    assert get_directory_contents(output_file) == expected


def test_awkward_lines(tmpdir):
    if tmpdir.join("output").check():
        tmpdir.join("output").remove(rec=True)
    output_path = tmpdir.mkdir("output")

    # We hit the deadline limit pretty query if we let Hypothesis generate
    # examples. Instead, let's provide a few of the ones that tripped us up.
    input_data = "\n".join(["", " ", "*", "\r", "some/path", "no-trailing-newline"])
    # splitlines() here as this turns the line w/ '\r' into an empty line, and
    # is what we'd do if we had Hypothesis generate data in the same way as
    # test_unique_named_work_items.
    lines = input_data.splitlines()
    # Enable universal newline decoding to better emulate actual files.
    input_stream = io.StringIO(input_data, newline=None)

    each = Each(
        command="cat",
        work_items=work_items_from_file(input_stream),
        destination=output_path,
        stdin=True,
    )
    each.clear_queue()

    expected = {line: [{"status": "0", "in": line, "out": line, "err": ""}] for line in lines}
    assert gather_output(output_path) == expected


@given(data=st.lists(st.text()))
def test_unique_named_work_items(data):
    """The names of the work items are unique even after case is smashed.

    This allows ``Each`` to safely create directories based on the names.
    """
    input_stream = io.StringIO("\n".join(data))
    item_names = [item.name for item in work_items_from_file(input_stream)]
    assert sorted(list({name.lower() for name in item_names})) == sorted(
        name.lower() for name in item_names
    )


@given(
    name=st.text(
        alphabet=string.ascii_letters + string.digits + "-_", min_size=1, max_size=MAX_NAME_LENGTH
    )
)
def test_friendly_names(name):
    """If a line has nothing weird in it, we give it a friendly name."""
    names = [item.name for item in work_items_from_file(io.StringIO(name))]
    assert names == ["%s-%s" % (hashlib.sha256(name.encode("utf-8")).hexdigest()[-8:], name)]


@given(
    name=st.text(
        alphabet=string.ascii_letters + string.digits + "-_",
        min_size=MAX_NAME_LENGTH,
        max_size=MAX_NAME_LENGTH * 2,
    )
)
def test_long_names(name):
    """Long lines with friendly names.

    If a line has nothing weird in it, but is really long, we give it a
    friendly, truncated name.
    """
    names = [item.name for item in work_items_from_file(io.StringIO(name))]
    hash_prefix = hashlib.sha256(name.encode("utf-8")).hexdigest()[-8:]
    assert names == ["%s-%s" % (hash_prefix, name[:MAX_NAME_LENGTH])]


@given(data=st.text())
def test_creates_pipe(data):
    """as_input_file returns a file descriptor from which we can read the original line."""
    line = data.split("\n")[0] if data else ""
    item = LineWorkItem(name="foo", line=line)
    fd = item.as_input_file()
    output_line = os.read(fd, len(line.encode("utf-8"))).decode("utf-8")
    assert output_line.strip("\n") == line
