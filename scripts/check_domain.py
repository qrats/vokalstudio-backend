#!/usr/bin/env python3
"""Fail the build if the domain layer grows a framework dependency.

``src/domain`` is plain Python on purpose: it is imported by the test suite
without Flask, SQLAlchemy or boto3 installed, and CI runs that suite with no
install step at all. This walks the package and rejects any import of a name
outside the standard library.
"""

import ast
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "domain")

FORBIDDEN = (
    "flask",
    "flask_restful",
    "flask_sqlalchemy",
    "sqlalchemy",
    "marshmallow",
    "celery",
    "boto3",
    "botocore",
    "requests",
    "redis",
    "jwt",
    "passlib",
    "googleapiclient",
    "src.models",
    "src.resources",
    "src.services",
    "src.tasks",
    "src.utils",
)


def imported_names(path):
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module)
    return found


def offences():
    problems = []
    for directory, _, filenames in os.walk(ROOT):
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            for name in sorted(imported_names(path)):
                for banned in FORBIDDEN:
                    if name == banned or name.startswith(banned + "."):
                        problems.append((os.path.relpath(path), name))
    return problems


def main():
    problems = offences()
    for path, name in problems:
        sys.stderr.write("{}: imports {}\n".format(path, name))
    if problems:
        sys.stderr.write("\nsrc/domain must stay free of framework imports\n")
        return 1
    print("src/domain is clean: no framework imports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
