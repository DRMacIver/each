"""Test helpers."""


def get_contents(path):
    """Get the contents of 'path' if it exists.

    Strips any trailing newlines.
    """
    return path.read().rstrip('\n') if path.check() else None


def get_directory_contents(path):
    """Get the contents of many files under 'path'."""
    return {child.basename: get_contents(child) for child in path.listdir()}


def gather_output(path):
    """Get all the output, grouped by input contents."""
    output = {}
    for f in path.listdir():
        contents = get_directory_contents(f)
        input_data = contents["in"]
        if input_data in output:
            output[input_data].append(contents)
        else:
            output[input_data] = [contents]
    return output
