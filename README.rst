====
Each
====

Each is a small batch processing utility designed to run some command on each
file in a directory and produce some output in another directory, with the
ability to resume processing if interrupted. Think of it as a slightly
idiosyncratic implementation of the map part of map/reduce, or a slightly more
robust version of the following bash script.

.. code-block:: bash

    for f in $source/* ; do
        DEST=$destination/$(basename $f)
        mkdir -p $DEST
        $command < $f > $DEST/$out 2> $DEST/err
        echo $? > $DEST/status

-----
Usage
-----

Usage is:

.. code-block:: bash

    each some-input-directory 'some command to run' --destination="output directory"

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

This has nice process management for running things in parallel, is good (and
I'm working on making it better)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Why isn't this tested with `Hypothesis <https://github.com/HypothesisWorks/hypothesis>`_?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Look, buddy, you're lucky it's tested at *all*.

(It probably will be at some point)

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
