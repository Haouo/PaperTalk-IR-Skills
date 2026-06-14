"""Shared pytest fixtures + path wiring for the paper2beamer test suite.

The helper scripts live in ``../scripts`` and import each other by bare module
name (``import ir_common``). Putting that directory on ``sys.path`` here lets the
tests import the modules directly, exactly as the scripts import one another at
runtime.
"""

from __future__ import annotations

import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture()
def fixtures_dir() -> str:
    return FIXTURES_DIR


@pytest.fixture()
def references_dir() -> str:
    return REFERENCES_DIR


@pytest.fixture()
def scripts_dir() -> str:
    return SCRIPTS_DIR
