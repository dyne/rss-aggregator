#!/usr/bin/env python
"""Compatibility wrapper that forwards the legacy test entrypoint to pytest."""

import os
import sys

import pytest


def _normalize_args(args):
    """Translate the historical runtests.py arguments into pytest paths."""
    if not args:
        return ["tests"]

    normalized = []
    for arg in args:
        if arg.startswith("-"):
            normalized.append(arg)
            continue
        if os.path.exists(arg):
            normalized.append(arg)
            continue
        if arg.endswith(".py"):
            normalized.append(os.path.join("tests", arg))
            continue
        normalized.append(arg)
    return normalized


if __name__ == "__main__":
    raise SystemExit(pytest.main(_normalize_args(sys.argv[1:])))
