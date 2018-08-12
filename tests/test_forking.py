import os

import attr
import pytest

from each import Each, each as each_module


def always_raises(exc):
    def accept(*args, **kwargs):
        raise exc()

    return accept


APPROVED_NAMES = {
    "listdir",
    "stat",
    "path",
    "makedirs",
    "O_EXCL",
    "O_WRONLY",
    "O_CREAT",
    "O_RDONLY",
    "open",
    "getpid",
}


@attr.s(slots=True)
class FakeOS(object):
    process_table = attr.ib(default=attr.Factory(dict))
    closed = attr.ib(default=attr.Factory(set))
    execs = attr.ib(default=attr.Factory(list))
    exec_error = attr.ib(default=None)
    next_fd = attr.ib(default=5)

    def execv(self, command, argv):
        self.execs.append((command, argv))
        if self.exec_error is not None:
            raise self.exec_error()

    def fork(self):
        return 0

    def _exit(self, n):
        raise SystemExit(n)

    def dup2(self, fd1, fd2, inheritable=True):
        self.process_table[fd2] = fd2

    def dup(self, fd1):
        res = self.next_fd
        self.next_fd += 1
        return res

    def close(self, fd):
        self.closed.add(fd)

    def __getattr__(self, name):
        assert name in APPROVED_NAMES
        return getattr(os, name)


@pytest.fixture
def child_test(monkeypatch):
    # We use an entire FakeOS module rather than monkeypatching methods on os
    # so as to not interfere with pytest's own use of it.
    fake_os = FakeOS()
    monkeypatch.setattr(each_module, "os", fake_os)
    return fake_os


@pytest.mark.parametrize("stdin", [False, True])
def test_will_show_exception_if_exec_fails(child_test, capsys, tmpdir, stdin):
    child_test.exec_error = PermissionError

    with pytest.raises(SystemExit):
        input_files = tmpdir.mkdir("input")
        input_files.join("hello").write("")

        each = Each(
            command="cat", source=input_files, destination=tmpdir.mkdir("output"), stdin=stdin
        )

        each.clear_queue()
        assert len(child_test.execs) == 1

    captured = capsys.readouterr()

    assert "PermissionError" in captured.err
    if stdin:
        assert child_test.process_table == {i: i for i in (0, 1, 2)}
    else:
        assert child_test.process_table == {i: i for i in (1, 2)}
        assert 0 in child_test.closed
