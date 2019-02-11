====
Each
====

Each is a shell command for running robust, parallel, for loops with good feedback mechanisms.

It's optimised for "medium scale" experiments, which are a bit too small and
ad hoc to run on a proper cluster (or maybe you just don't *have* a proper cluster. I don't),
but are slow enough that restarting them from scratch would be painful and, ideally,
parallel enough that if you happen to have a sixteen core server lying around to run them on you really want to be using all sixteen of those cores.

Primary usage of each is a more robust version of the following bash for loop:

.. code-block:: bash

    for f in "$source"/* ; do
        DEST="$destination"/$(basename $f)
        mkdir -p "$DEST"
        "$command" < "$f" > "$DEST/out" 2> "$DEST/err"
        echo $? > "$DEST/status"
    done

The same could be written using each as follows:

.. code-block:: bash

	each "$source" "$command" --destination="$destination"

As well as being shorter and more readable, writing this with each gets you:

1. Automatic parallelism. You can control how many processes are run with ``--processes=n``,
   but it defaults to using all but one of the cores available (or one on a single core machine).
2. Automatic resume - if each dies, when it next starts up it will resume from where it left off.
3. Feedback on progress, with good predictive analytics about when the process will finish (still a work in progress but the basics are there).

Later you will also get good logic for retrying errors, but I haven't written that bit yet.

Each is still a bit early days, so it likely has some rough edges, but it's well tested and has been making my life vastly better already.

-----
Usage
-----

Usage is:

.. code-block:: bash

    each some-input-directory 'some command to run' --destination="output directory"

Commands can be arbitrary shell commands (and will be run by ``$SHELL -c 'some command to run'`` by default).

By default, the file's contents will be passed to the child process's stdin. If you want to pass the file by name, you can use the special string `{}`.
If you do, the file to be processed will be substituted for it (with its absolute path name) and stdin will be empty.

More advanced usage options are available from ``each --help``.

--------------------------------
Frequently Anticipated Questions
--------------------------------

~~~~
Why?
~~~~

I have a bunch of experiments that are basically "run this long running task on
each of these files" with the tasks having varying degrees of flakiness, and I
kept finding myself writing bad versions of this, so I thought I would solve
the problem once and for all.

Main features over the bash loop version:

1. You don't risk learning how to write more bash than you want to.
2. It resumes from where it left off if you kill it.
3. Automatic parallelism
4. You get a cool progress bar.
5. When I get around to writing better retry features you'll get those for free.

~~~~~~~~~~~~~~~~~~~~
How do I install it?
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

  pip install each

~~~~~~~~~~~~~~~~~~~~
What does it run on?
~~~~~~~~~~~~~~~~~~~~

Probably anything unixy. I've developed and tested it on Linux (including WSL, the Windows
10 Linux Subsystem), but it's likely to work unmodified on OSX. It's unlikely to work on
Windows. I'm not against Windows support if someone wants to contribute it, but I won't
be writing it myself and it's a fairly unixy sort of tool.


~~~~~~~~~~~~~~~~~~
Should I use this?
~~~~~~~~~~~~~~~~~~

Eh, maybe. I'm finding it pretty helpful but it may be very idiosyncratic to my
usage.

If you try it and it doesn't work for you, file an issue or make a PR.
I'm happy for it to be generally useful but I don't plan to sink a huge amount
of time into supporting it.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Will you make it work on Python 2?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Will you release it under a more permissive license?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Also no.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
I don't like these answers. What should I use instead?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I dunno. Maybe `bashreduce <https://github.com/erikfrey/bashreduce>`_?
