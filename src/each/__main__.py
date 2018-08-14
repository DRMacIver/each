import multiprocessing as mp
from datetime import datetime, timedelta

import click
from tqdm import tqdm

from each import SHELL, Each


@click.command(
    help="""
each runs a command on each file in a source directory, writing its results to
files in a destination directory.

Roughly equivalent to a more robust version of the following bash loop:

\b
for f in $source/* ; do
    DEST=$destination/$(basename $f)
    mkdir -p $DEST
    $command < $f > $DEST/$out 2> $DEST/err
    echo $? > $DEST/status
done

Unlike this loop it comes with a variety of ways to configure it,
will run its body in parallel, and handles resuming from interruptions and
such robustly.
"""
)
@click.argument("source")
@click.argument("command")
@click.option(
    "--shell",
    default=SHELL,
    help="""
The shell to use to interpret the command.
""",
)
@click.option(
    "--destination",
    default="",
    help="""
The destination directory. Defaults to the name of the input directory with
"-results" appended to the end.
""".replace(
        "\n", " "
    ),
)
@click.option(
    "--recreate/--no-recreate",
    default=False,
    help="""
By default each will not attempt to recreate files that have already been
successfully processed. If this is set to true, existing files will be
overwritten.
""".replace(
        "\n", " "
    ),
)
@click.option(
    "--processes",
    default=max(1, mp.cpu_count() - 1),
    help="""
The number of child processes to run.""",
)
@click.option(
    "--stdin/--no-stdin",
    default=None,
    help="""
If --stdin is passed the contents of the file will be passed to the command's
stdin, otherwise its name will be substituted in for the string {} in the command.
By default will use stdin unless {} is present in the command.
""".replace(
        "\n", " "
    ),
)
def main(command, source, destination, recreate, processes, stdin, shell):
    if not destination:
        destination = source.rstrip("/") + "-results"

    if stdin is None:
        stdin = "{}" not in command

    with tqdm() as pb:

        def new_prediction(p):
            now = datetime.now()
            eta = now + timedelta(seconds=p.percentile(99))

            if (eta - now <= timedelta(days=1)) and eta.day == now.day:
                pb.set_postfix(eta=eta.strftime("%H:%M:%S"))
            else:
                pb.set_postfix(eta=eta.strftime("%Y-%m-%d %H:%M"))

        each = Each(
            source=source,
            shell=shell,
            destination=destination,
            command=command,
            progress_callback=pb.update,
            prediction_callback=new_prediction,
            recreate=recreate,
            processes=processes,
            stdin=stdin,
        )
        pb.total = pb.n + len(each.work_queue)
        pb.refresh()

        each.clear_queue()


if __name__ == "__main__":
    main()
