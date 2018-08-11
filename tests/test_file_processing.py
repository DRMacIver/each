from each import Each
import pytest


@pytest.mark.parametrize("processes", [1, 2, 4])
@pytest.mark.parametrize("stderr", [False, True])
def test_processes_each_file(tmpdir, processes, stderr):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    for i in range(10):
        p = input_files.join("%d.txt" % (i,))
        p.write("hello %d" % (i,))
    each = Each(
        command="cat >&2" if stderr else "cat",
        source=input_files,
        destination=output_files,
        processes=processes,
    )
    each.clear_queue()

    for i, f in enumerate(output_files.listdir()):
        out = f.join("out")
        err = f.join("err")
        status = f.join("status")

        assert out.check()
        assert err.check()
        assert status.check()

        if stderr:
            err, out = out, err

        assert err.read().strip() == ""
        assert out.read().strip() == "hello %d" % (i,)
        assert status.read().strip() == "0"


def test_does_not_recreate_by_default(tmpdir):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    marker = tmpdir.join("marker")

    marker.write("stuff")

    input_files.join("hello").write("")

    for _ in range(2):
        each = Each(
            command="cat %s" % (marker,),
            stdin=False,
            source=input_files,
            destination=output_files,
            processes=1,
        )
        each.clear_queue()

        out = output_files.join("hello").join("out").read()

        assert "stuff" in out
        assert "things" not in out

        marker.write("things")


@pytest.mark.parametrize("bad_crash", [False, True])
def test_recreates_if_set(tmpdir, bad_crash):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    marker = tmpdir.join("marker")

    marker.write("stuff")

    input_files.join("hello").write("")

    for v in ["stuff", "things"]:
        marker.write(v)

        each = Each(
            command="cat %s" % (marker,),
            stdin=False,
            source=input_files,
            destination=output_files,
            processes=1,
            recreate=True,
        )
        each.clear_queue()

        assert v == output_files.join("hello").join("out").read().strip()

        if bad_crash:
            # This could happen in real life if the parent process were killed.
            output_files.join("hello").join("status").remove()


def test_can_handle_disappearing_files(tmpdir):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    input_files.join("hello").write("")
    gb = input_files.join("goodbye")
    gb.write("")

    each = Each(
        command="cat",
        stdin=False,
        source=input_files,
        destination=output_files,
        processes=1,
        recreate=True,
    )

    assert len(each.work_queue) == 2

    gb.remove()

    each.clear_queue()

    assert len(output_files.listdir()) == 1
