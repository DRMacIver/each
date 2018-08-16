"""Test helpers."""


def get_contents(path):
    """Get the contents of 'path' if it exists."""
    return path.read().strip() if path.check() else None


def get_directory_contents(path):
    """Get the contents of many files under 'path'."""
    return {child.basename: get_contents(child) for child in path.listdir()}
