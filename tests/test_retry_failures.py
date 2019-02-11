import sys

from each import Each, work_items_from_path


def test_retries_failures_from_a_previous_run(tmpdir):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")

    input_files.join("hello").write("")

    for command, status in [("false", 1), ("true", 0)]:
        each = Each(
            command=command,
            retries=1,
            stdin=False,
            work_items=work_items_from_path(input_files),
            destination=output_files,
        )
        each.clear_queue()

        result = int(output_files.join("hello").join("status").read().strip())

        assert result == status


UPDATE_COUNTER = """
import sys

if __name__ == '__main__':
    counter = %r

    with open(counter, 'r') as i:
        n = int(i.read().strip())

    with open(counter, 'w') as o:
        o.write(str(n + 1))

    sys.exit(1)
"""


def test_retries_failures_in_the_current_run(tmpdir):
    counter = tmpdir.join("counter")
    counter.write("0")

    update_counter = tmpdir.join("update_counter.py")
    update_counter.write(UPDATE_COUNTER % (str(counter),))

    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")

    input_files.join("hello").write("")

    each = Each(
        command="%s %s" % (sys.executable, update_counter),
        retries=2,
        stdin=False,
        work_items=work_items_from_path(input_files),
        destination=output_files,
    )
    each.clear_queue()

    assert counter.read() == "3"
