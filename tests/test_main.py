import os
import subprocess
import sys
from shutil import which

import pytest


@pytest.mark.parametrize("cat", ["cat", "cat {}"])
def test_processes_each_file(tmpdir, cat):
    input_path = tmpdir.mkdir("input")
    output_path = tmpdir.mkdir("output")
    for i in range(10):
        p = input_path.join("%d.txt" % (i,))
        p.write("hello %d" % (i,))

    subprocess.check_call(
        [sys.executable, "-m", "each", str(input_path), cat, "--destination=%s" % (output_path,)]
    )

    output_files = sorted(output_path.listdir())
    assert output_files == [output_path.join("%d.txt" % (i,)) for i in range(10)]

    for i, f in enumerate(output_files):
        out = f.join("out")
        err = f.join("err")
        status = f.join("status")

        assert out.check()
        assert err.check()
        assert status.check()

        assert err.read().strip() == ""
        assert out.read().strip() == "hello %d" % (i,)
        assert status.read().strip() == "0"


@pytest.mark.parametrize("echo", ["cat", "echo {}"])
def test_processes_each_line(tmpdir, echo):
    """When given a file (not a directory) as input, ``each`` will run the given
    command on each *line* of the file, creating an output directory for that
    looks a lot like the output directory you get with a directory input,
    except that each directory also has an ``in`` file, which contains the
    contents of the input line.
    """
    input_path = tmpdir.join("input")
    output_path = tmpdir.mkdir("output")
    with input_path.open("w") as input_file:
        for i in range(10):
            input_file.write("hello %d\n" % (i,))

    subprocess.check_call(
        [sys.executable, "-m", "each", str(input_path), echo, "--destination=%s" % (output_path,)]
    )

    output_files = sorted(output_path.listdir())
    assert output_files == [output_path.join("hello %d" % (i,)) for i in range(10)]

    for i, f in enumerate(output_files):
        out = f.join("out")
        err = f.join("err")
        status = f.join("status")

        assert list(map(get_contents, [status, out, err])) == ["0", "hello %d" % (i,), ""]


def get_contents(path):
    """Get the contents of 'path' if it exists."""
    return path.read().strip() if path.check() else None


@pytest.mark.parametrize("shell", [which("sh"), which("bash")])
def test_respects_shell_argument(tmpdir, shell):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    input_files.join("sh").write("")

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "each",
            str(input_files),
            "echo $0",
            "--destination=%s" % (output_files,),
            "--stdin",
            "--shell=%s" % (shell,),
        ]
    )

    written = output_files.join("sh").join("out").read().strip()

    assert os.path.basename(written) == os.path.basename(shell)
