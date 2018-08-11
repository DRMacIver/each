from each import Each


def test_processes_each_file(tmpdir):
    input_files = tmpdir.mkdir("input")
    output_files = tmpdir.mkdir("output")
    for i in range(10):
        p = input_files.join("%d.txt" % (i,))
        p.write("hello %d" % (i,))
    each = Each(command="cat", source=input_files, destination=output_files)
    each.clear_queue()

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
