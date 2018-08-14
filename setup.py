import os

import setuptools


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


SOURCE = local_file("src")
README = local_file("README.rst")

setuptools_version = tuple(map(int, setuptools.__version__.split(".")[:2]))

# Assignment to placate pyflakes. The actual version is from the exec that
# follows.
__version__ = None

with open(local_file("src/each/version.py")) as o:
    exec(o.read())

assert __version__ is not None

setuptools.setup(
    name="each",
    version=__version__,
    author="David R. MacIver",
    author_email="david@drmaciver.com",
    packages=setuptools.find_packages(SOURCE),
    package_dir={"": SOURCE},
    url=("https://github.com/DRMacIver/each/"),
    license="GPL v3",
    description="A tool for running programs on many inputs",
    zip_safe=False,
    install_requires=["attrs>=18.0.0", "click", "tqdm", "numpy"],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    classifiers=[
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    entry_points={"console_scripts": ["each=each.__main__:main"]},
    long_description=open(README).read(),
)
