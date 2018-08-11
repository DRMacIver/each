import attr
import multiprocessing as mp
import os
import heapq
import sys
import click
from tqdm import tqdm
import traceback
import shutil


def run_command(source_file, target_file, command):
    pass


@attr.s()
class WorkInProgress():
    pid = attr.ib()
    source_file = attr.ib()
    out_file = attr.ib()
    err_file = attr.ib()


@attr.s()
class Each(object):
    source = attr.ib()
    destination = attr.ib()
    command = attr.ib()
    n_processes = attr.ib()
    recreate = attr.ib()
    stdin = attr.ib()

    score_file = attr.ib(
        default=lambda s: os.stat(s).st_size
    )

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

    suffix = attr.ib(default=None)
    progress_callback = attr.ib(default=lambda: None)

    work_in_progress = attr.ib(default=attr.Factory(dict), init=False)
    work_queue = attr.ib(default=None, init=False)

    def clear_queue(self):
        while self.work_in_progress or self.work_queue:
            while (
                self.work_queue and
                len(self.work_in_progress) < self.n_processes
            ):
                _, source_file = heapq.heappop(self.work_queue)
                self.progress_callback()

                name = os.path.basename(source_file)

                out_file = os.path.join(self.destination, name)
                if self.suffix:
                    out_file += ('.' + self.suffix)
                err_file = out_file + '.error'
                if not os.path.exists(source_file):
                    continue
                if (
                    os.path.exists(out_file) or
                    os.path.exists(err_file)
                ):
                    if self.recreate:
                        for f in [out_file, err_file]:
                            if os.path.exists(f):
                                os.unlink(f)
                    else:
                        continue
                pid = None
                pid = os.fork()
                if pid != 0:
                    self.work_in_progress[pid] = WorkInProgress(
                        pid=pid, source_file=source_file,
                        out_file=out_file,
                        err_file=err_file,
                    )
                else:
                    try:
                        if self.stdin:
                            filein = os.open(source_file, os.O_RDONLY)
                            os.dup2(filein, sys.stdin.fileno())
                        else:
                            os.close(sys.stdin.fileno)
                        flags = os.O_EXCL | os.O_CREAT | os.O_WRONLY
                        original_err = os.dup(sys.stderr.fileno())
                        original_out = os.dup(sys.stdout.fileno())
                        err = os.open(err_file, os.O_EXCL | os.O_CREAT)
                        out = os.open(out_file, flags)
                        os.dup2(err, sys.stderr.fileno())
                        os.dup2(out, sys.stdout.fileno())
                        argv = [os.path.basename(self.command)]
                        if not self.stdin:
                            argv.append(os.path.abspath(source_file))
                        os.execv(self.command, argv)
                    except:
                        os.dup2(original_out, sys.stdout.fileno())
                        os.dup2(original_err, sys.stderr.fileno())
                        traceback.print_exc()
                        os._exit(1)
            if self.work_in_progress:
                pid, result = os.wait()
                work_item = self.work_in_progress.pop(pid)
                if result == 0:
                    os.unlink(work_item.err_file)
                else:
                    tqdm.write("Failed %r %r" % (work_item, result))
                    os.unlink(work_item.out_file)


@click.command()
@click.argument('command')
@click.argument('source')
@click.option('--destination', default='')
@click.option('--recreate/--no-recreate', default=False)
@click.option('--processes', default=max(1, mp.cpu_count() - 1))
@click.option('--stdin/--by-name', default=True)
def main(command, source, destination, recreate, processes, stdin):
    if not destination:
        destination = source.rstrip("/") + '-results'

    if not os.path.exists(command):
        command = shutil.which(command)

    with tqdm() as pb:
        each = Each(
            source=source, destination=destination,
            command=command,
            progress_callback=pb.update, recreate=recreate,
            n_processes=processes, stdin=stdin,
        )
        pb.total = len(each.work_queue)
        pb.refresh()

        each.clear_queue()


if __name__ == '__main__':
    main()
