"""Common development operations."""
import os
import os.path

from invoke import task


def log(message):
    print(message)


def relative_to_this_file(*path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), *path)


@task
def style(c):
    """Use isort, black, and flake8 to fix and check Python style and complexity."""
    with c.cd(relative_to_this_file()):
        log("Running isort")
        # Use isort settings which are compatible with black.
        c.run(
            "isort --multi-line=3 --trailing-comma --force-grid-wrap=0 "
            "--combine-as --line-width=88 -y"
        )
        log("Running black")
        c.run("black .")
        log("Checking coding style")
        c.run(
            "flake8 "
            '--exclude=".svn,CVS,.bzr,.hg,.git,__pycache__,._*" '
            "--max-line-length=88 "
            "--max-complexity=9 ."
        )


@task
def clean(c):
    """Remove all generated files (.pyc, .coverage, .egg, etc)."""
    with c.cd(relative_to_this_file()):
        log("Cleaning out all derived files")
        c.run('find -name "*.pyc" | xargs rm -f')
        c.run("find -name .coverage | xargs rm -f")
        c.run("find -name .DS_Store | xargs rm -f")  # Created by OSX
        c.run("find -name ._DS_Store | xargs rm -f")  # Created by OSX
        c.run('find -name "._*.*" | xargs rm -f')  # Created by Caret
        c.run("rm -rf build")
        c.run("rm -rf dist")
        c.run("rm -rf *.egg")
        c.run("rm -rf encapsia-api-*")
