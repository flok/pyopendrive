"""Behavior checks against ASAM's OpenDRIVE 1.9.0 example corpus."""

from __future__ import annotations

from fetch_testdata import CORPUS_PATH

from pyopendrive import OpenDrive, OpenDriveVersion


def test_all_official_examples_load() -> None:
    examples = sorted(CORPUS_PATH.rglob("*.xodr"))
    assert examples, "run tests/fetch_testdata.py before pytest"

    for example in examples:
        road_map = OpenDrive.load(example)
        assert isinstance(road_map.format_version, OpenDriveVersion), example
        assert road_map.roads, example
