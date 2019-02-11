import hashlib
import os
import re
import shlex
import shutil
import time
import traceback
from abc import ABC, abstractmethod
from collections import Counter
from random import Random

import attr

from each.junkdrawer import Timeout, timeout
from each.prediction import predict_timing

# We can't use the normal sys ones within pytest if we want to actually operate
# on the underlying unix file descriptors.
STDIN = 0
STDOUT = 1
STDERR = 2

SHELL = os.environ.get("SHELL") or shutil.which("bash") or shutil.which("sh")


@attr.s()
class WorkInProgress:
    pid = attr.ib()
    started = attr.ib()
    work_item = attr.ib()
    out_file = attr.ib()
    err_file = attr.ib()
    status_file = attr.ib()


class WorkItem(ABC):
    """A thing to processed by ``Each``."""

    """A name for this work item that can be used as a filename."""
    name = NotImplemented

    @abstractmethod
    def exists(self):
        """Whether or not this work item still exists."""

    @abstractmethod
    def as_input_file(self):
        """This work item as a file descriptor.

        This file descriptor is used as STDIN on a user-provided command.
        """

    @abstractmethod
    def as_argument(self):
        """This work item as a command-line argument."""

    @abstractmethod
    def write_in_file(self, path):
        """Create a file at 'path' that contains the input data for this work item."""


@attr.s()
class FileWorkItem(WorkItem):
    """A file to be processed by ``Each``."""

    """A name for this work item that can be used as a filename."""
    name = attr.ib()

    """The location of the file on disk."""
    path = attr.ib()

    def exists(self):
        """A file work item exists only if the file exists."""
        return os.path.exists(self.path)

    def as_input_file(self):
        return os.open(self.path, os.O_RDONLY)

    def as_argument(self):
        return os.path.abspath(self.path)

    def write_in_file(self, path):
        """The ``in`` file is a symlink to the original file."""
        os.symlink(os.path.abspath(self.path), path)


@attr.s()
class LineWorkItem(WorkItem):
    """A line to be processed by ``Each``."""

    """A name for this work item that can be used as a filename."""
    name = attr.ib()

    """The line itself, including line ending, as text."""
    line = attr.ib()

    def exists(self):
        """Whether or not this work item still exists.

        A line always exists.
        """
        return True

    def as_input_file(self):
        r, w = os.pipe()
        os.write(w, self.line.encode("utf-8"))
        os.close(w)
        return r

    def as_argument(self):
        return self.line.rstrip("\r\n")

    def write_in_file(self, path):
        """The ``in`` file for a line work item is a file with just that line."""
        with open(path, "w") as in_file:
            in_file.write(self.line)


def work_items_from_path(path):
    """Load work items from a user-supplied path.

    If 'path' is a directory, our work items are files. If it's a # file, our
    work items are lines.
    """
    try:
        return work_items_from_directory(path)
    except NotADirectoryError:
        with open(path, "r") as stream:
            return work_items_from_lines(stream)


def work_items_from_directory(path):
    """Get a list of work items from a directory.

    Each file in the directory is a work item.
    """
    return (FileWorkItem(name=s, path=os.path.join(path, s)) for s in os.listdir(path))


"""What we consider a 'simple name'.

These are appended to the hashes of lines when generating output,
as a convenience to the humans who must contend with it.
"""
simple_name_re = re.compile("^[A-Za-z0-9_-]+$")


"""The longest simple name we allow as a suffix to the generated filename."""
MAX_SIMPLE_NAME_SUFFIX_LENGTH = 100


def work_items_from_lines(stream):
    """Yield a series of work items derived from an iterator of lines.

    We expect each line to be a ``str`` with the newline already stripped, as
    happens automatically with open files, or with ``StringIO`` with universal
    newline decoding.
    """
    items = {}
    for line in stream:
        name = hashlib.sha256(line.encode("utf-8")).hexdigest()[-8:]
        if simple_name_re.match(line.strip()):
            name += "-" + line.strip()[:MAX_SIMPLE_NAME_SUFFIX_LENGTH]
        items[name] = LineWorkItem(name, line)
    return items.values()


@attr.s()
class Each(object):
    """Run a single command over many things.

    These things can be either lines in a file, or files in a directory.
    """

    """A list of work items to process.

    The names of the items must all be valid filesystem names, and must not
    clash with each other when written to the filesystem.

    i.e. they must be unique, and if your filesystem is case-insensitive, they
    must be unique after being lower-cased.
    """
    work_items = attr.ib()
    """A path to a directory where we will create the output files."""
    destination = attr.ib()
    """The command to run over the source data. This is a single string."""
    command = attr.ib()
    """The number of processes to run in parallel."""
    processes = attr.ib(default=1)
    recreate = attr.ib(default=False)
    stdin = attr.ib(default=True)
    shell = attr.ib(default=SHELL)
    random = attr.ib(default=attr.Factory(Random))
    runtimes = attr.ib(default=attr.Factory(list))
    prediction = attr.ib(default=None)
    wait_timeout = attr.ib(default=1.0)
    retries = attr.ib(default=0)
    failure_counts = attr.ib(default=attr.Factory(Counter))

    def __attrs_post_init__(self):
        self.work_queue = []

        try:
            os.makedirs(self.destination)
        except FileExistsError:
            pass

        for work_item in self.work_items:
            status_file = os.path.join(self.destination, work_item.name, "status")

            previous_status = None

            try:
                with open(status_file) as i:
                    previous_status = int(i.read().strip())
            except (ValueError, FileNotFoundError):
                pass

            if previous_status is not None:
                discard = not self.recreate

                if previous_status != 0 and self.retries > 0:
                    self.failure_counts[work_item.name] += 1
                    discard = False
            else:
                discard = False

            if discard:
                self.progress_callback()
            else:
                self.work_queue.append(work_item)
        # By iterating in random order, we can paradoxically get much better predictability
        # about the final run time! This allows us to conclude the times we've seen so far
        # are reasonably representative of the times we will see in future.
        self.random.shuffle(self.work_queue)

    progress_callback = attr.ib(default=lambda: None)
    prediction_callback = attr.ib(default=lambda p: None)

    work_in_progress = attr.ib(default=attr.Factory(dict), init=False)
    work_queue = attr.ib(default=None, init=False)

    def fill_work_in_progress(self):
        while self.work_queue and len(self.work_in_progress) < self.processes:
            work_item = self.work_queue.pop()
            if not work_item.exists():
                self.progress_callback()
                continue

            base_dir = os.path.join(self.destination, work_item.name)

            in_file = os.path.join(base_dir, "in")
            out_file = os.path.join(base_dir, "out")
            err_file = os.path.join(base_dir, "err")
            status_file = os.path.join(base_dir, "status")

            if os.path.exists(base_dir):
                for f in [in_file, out_file, err_file, status_file]:
                    if os.path.exists(f):
                        os.unlink(f)

            try:
                os.makedirs(base_dir)
            except FileExistsError:
                pass

            work_item.write_in_file(in_file)

            pid = None
            pid = os.fork()
            if pid != 0:
                self.work_in_progress[pid] = WorkInProgress(
                    pid=pid,
                    work_item=work_item,
                    out_file=out_file,
                    err_file=err_file,
                    status_file=status_file,
                    started=time.monotonic(),
                )
            else:
                try:
                    original_err = os.dup(STDERR)
                    original_out = os.dup(STDOUT)
                    if self.stdin:
                        filein = work_item.as_input_file()
                        os.dup2(filein, STDIN)
                    else:
                        os.close(STDIN)
                    flags = os.O_EXCL | os.O_CREAT | os.O_WRONLY
                    err = os.open(err_file, flags)
                    out = os.open(out_file, flags)
                    os.dup2(err, STDERR)
                    os.dup2(out, STDOUT)
                    argv = [os.path.basename(self.shell), "-c", self.command]
                    if not self.stdin:
                        argv[-1] = argv[-1].replace("{}", shlex.quote(work_item.as_argument()))
                    os.execv(self.shell, argv)
                except:  # noqa
                    os.dup2(original_out, STDOUT)
                    os.dup2(original_err, STDERR)
                    traceback.print_exc()
                    os._exit(1)

    def collect_completed_work(self):
        best_timeout = self.wait_timeout

        while self.work_in_progress:
            try:
                with timeout(best_timeout):
                    pid, result = os.wait()
            except Timeout:
                return
            # Once we've collected one task we want to time out very
            # quickly on the others so we don't delay rescheduling
            # work.
            best_timeout = 0.05 * self.wait_timeout
            item_in_progress = self.work_in_progress.pop(pid)
            self.runtimes.append(time.monotonic() - item_in_progress.started)
            with open(item_in_progress.status_file, "w") as o:
                print(result >> 8, file=o)
            if result != 0 and self.failure_counts[item_in_progress.work_item.name] < self.retries:
                self.work_queue.append(item_in_progress.work_item)
                self.failure_counts[item_in_progress.work_item.name] += 1
            else:
                self.progress_callback()

    def update_predicted_timing(self):
        assert (len(self.work_in_progress) == self.processes) or (len(self.work_queue) == 0)
        if not self.work_in_progress:
            return
        now = time.monotonic()
        if self.prediction is None or self.prediction[0] <= now - 2:
            self.prediction = (
                now,
                predict_timing(
                    historical_times=self.runtimes,
                    current_queue=[now - w.started for w in self.work_in_progress.values()],
                    remaining_tasks=len(self.work_queue),
                    seed=self.random.getrandbits(32),
                ),
            )
            self.prediction_callback(self.prediction[1])

    def clear_queue(self):
        while self.work_in_progress or self.work_queue:
            self.fill_work_in_progress()
            self.update_predicted_timing()
            self.collect_completed_work()
