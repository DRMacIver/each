import click
from tqdm import tqdm
from each import Each
import multiprocessing as mp


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
