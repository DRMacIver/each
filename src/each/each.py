import os
import shlex
import shutil
import time
import traceback
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
    source_file = attr.ib()
    out_file = attr.ib()
    err_file = attr.ib()
    status_file = attr.ib()


@attr.s()
class Each(object):
    source = attr.ib()
    destination = attr.ib()
    command = attr.ib()
    processes = attr.ib(default=1)
    recreate = attr.ib(default=False)
    stdin = attr.ib(default=True)
    shell = attr.ib(default=SHELL)
    random = attr.ib(default=attr.Factory(Random))
    runtimes = attr.ib(default=attr.Factory(list))
    prediction = attr.ib(default=None)
    wait_timeout = attr.ib(default=1.0)

    def __attrs_post_init__(self):
        self.work_queue = [os.path.join(self.source, s) for s in os.listdir(self.source)]
        # By iterating in random order, we can paradoxically get much better predictability
        # about the final run time! This allows us to conclude the times we've seen so far
        # are reasonably representative of the times we will see in future.
        self.random.shuffle(self.work_queue)
        try:
            os.makedirs(self.destination)
        except FileExistsError:
            pass

    progress_callback = attr.ib(default=lambda: None)
    prediction_callback = attr.ib(default=lambda p: None)

    work_in_progress = attr.ib(default=attr.Factory(dict), init=False)
    work_queue = attr.ib(default=None, init=False)

    def fill_work_in_progress(self):
        while self.work_queue and len(self.work_in_progress) < self.processes:
            source_file = self.work_queue.pop()
            if not os.path.exists(source_file):
                self.progress_callback()
                continue
            name = os.path.basename(source_file)

            base_dir = os.path.join(self.destination, name)

            out_file = os.path.join(base_dir, "out")
            err_file = os.path.join(base_dir, "err")
            status_file = os.path.join(base_dir, "status")

            if os.path.exists(base_dir):
                if self.recreate:
                    for f in [out_file, err_file, status_file]:
                        if os.path.exists(f):
                            os.unlink(f)
                else:
                    self.progress_callback()
                    continue

            try:
                os.makedirs(base_dir)
            except FileExistsError:
                pass

            pid = None
            pid = os.fork()
            if pid != 0:
                self.work_in_progress[pid] = WorkInProgress(
                    pid=pid,
                    source_file=source_file,
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
                        filein = os.open(source_file, os.O_RDONLY)
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
                        argv[-1] = argv[-1].replace("{}", shlex.quote(os.path.abspath(source_file)))
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
            self.progress_callback()
            work_item = self.work_in_progress.pop(pid)
            self.runtimes.append(time.monotonic() - work_item.started)
            with open(work_item.status_file, "w") as o:
                print(result >> 8, file=o)

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
