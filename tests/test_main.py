import os
import subprocess
import sys
from shutil import which

import pytest


def test_processes_each_file(tmpdir):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    for i in range(10):
        p = input_files.join("%d.txt" % (i,))
        p.write("hello %d" % (i,))

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "each",
            str(input_files),
            "cat",
            "--destination=%s" % (output_files,),
        ]
    )

    for i, f in enumerate(output_files.listdir()):
        out = f.join("out")
        err = f.join("err")
        status = f.join("status")

        assert out.check()
        assert err.check()
        assert status.check()

        assert err.read().strip() == ""
        assert out.read().strip() == "hello %d" % (i,)
        assert status.read().strip() == "0"


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
