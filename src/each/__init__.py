import attr
import os
import heapq
import traceback
import shutil
import shlex

# We can't use the normal sys ones within pytest if we want to actually operate
# on the underlying unix file descriptors.
STDIN = 0
STDOUT = 1
STDERR = 2

SHELL = shutil.which("bash") or shutil.which("sh")


def run_command(source_file, target_file, command):
    pass


@attr.s()
class WorkInProgress:
    pid = attr.ib()
    source_file = attr.ib()
    out_file = attr.ib()
    err_file = attr.ib()
    status_file = attr.ib()


@attr.s()
class Each(object):
    source = attr.ib()
    destination = attr.ib()
    command = attr.ib()
    n_processes = attr.ib(default=1)
    recreate = attr.ib(default=False)
    stdin = attr.ib(default=True)

    score_file = attr.ib(default=lambda s: os.stat(s).st_size)

    def __attrs_post_init__(self):
        self.work_queue = [
            (self.score_file(t), t)
            for s in os.listdir(self.source)
            for t in [os.path.join(self.source, s)]
        ]
        heapq.heapify(self.work_queue)
        try:
            os.makedirs(self.destination)
        except FileExistsError:
            pass

    progress_callback = attr.ib(default=lambda: None)

    work_in_progress = attr.ib(default=attr.Factory(dict), init=False)
    work_queue = attr.ib(default=None, init=False)

    def clear_queue(self):
        while self.work_in_progress or self.work_queue:
            while self.work_queue and len(self.work_in_progress) < self.n_processes:
                _, source_file = heapq.heappop(self.work_queue)
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
                    continue

                pid = None
                pid = os.fork()
                if pid != 0:
                    self.work_in_progress[pid] = WorkInProgress(
                        pid=pid,
                        source_file=source_file,
                        out_file=out_file,
                        err_file=err_file,
                        status_file=status_file,
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
                        argv = [os.path.basename(SHELL), "-c", self.command]
                        if not self.stdin:
                            argv[-1] += " " + shlex.quote(os.path.abspath(source_file))
                        os.execv(SHELL, argv)
                    except:
                        os.dup2(original_out, STDOUT)
                        os.dup2(original_err, STDERR)
                        traceback.print_exc()
                        os._exit(1)
            if self.work_in_progress:
                pid, result = os.wait()
                self.progress_callback()
                work_item = self.work_in_progress.pop(pid)
                with open(work_item.status_file, "w") as o:
                    print(result >> 8, file=o)
