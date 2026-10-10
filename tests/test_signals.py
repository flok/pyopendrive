"""Independently authored fixtures for OpenDRIVE 1.9 sections 14.1 to 14.5."""

from dataclasses import FrozenInstanceError
from io import StringIO

import pytest

from pyopendrive import OpenDriveMap, OpenDriveParseError

SIGNAL = (
    '<signal id="s01" s="4" t="-2" zOffset="1" dynamic="no"'
    ' orientation="+" type="274" subtype="50"'
)


def load(content: str, revision: int = 9, namespace: str = ""):
    return OpenDriveMap.load(
        StringIO(
            f'<OpenDRIVE {namespace}><header revMajor="1" revMinor="{revision}"/>'
            '<road id="r01" length="20"'
            f' junction="-1"><signals>{content}</signals></road></OpenDRIVE>'
        )
    )


def test_signal_and_reference_preserve_source_values_and_order():
    result = load(
        SIGNAL + ' temporary="true" invalidated="0" country="DE" value="50"'
        ' unit="km/h" length=".2">'
        '<validity fromLane="-2" toLane="-1" layer="temporary"/>'
        '<dependency id="s02" type="supplement"/>'
        '<reference elementId="o01" elementType="object" type="stopLine"/>'
        '</signal><signalReference id="s01" s="9" t="0" orientation="none">'
        '<validity fromLane="-1" toLane="1"/></signalReference>',
        namespace='xmlns="urn:test"',
    )
    road = result.roads[0]
    signal = road.signals[0]
    assert (signal.id, signal.s, signal.dynamic, signal.value, signal.length) == (
        "s01",
        4.0,
        False,
        50.0,
        0.2,
    )
    assert signal.temporary is True and signal.invalidated is False
    assert signal.validity[0].layer == "temporary"
    assert signal.dependencies[0].id == "s02"
    assert signal.references[0].element_id == "o01"
    assert road.signal_references[0].validity[0].layer is None
    assert result.diagnostics == ()
    with pytest.raises(FrozenInstanceError):
        signal.id = "changed"


def test_signal_omissions_and_empty_container():
    signal = load(SIGNAL + "/>").roads[0].signals[0]
    assert signal.temporary is None and signal.invalidated is None
    assert signal.width is None and signal.validity == ()
    road = load("").roads[0]
    assert road.signals == () and road.signal_references == ()


@pytest.mark.parametrize("attribute", ['s="nan"', 'dynamic="true"', 'temporary="yes"'])
def test_invalid_signal_attributes_have_element_context(attribute):
    content = SIGNAL
    name = attribute.split("=")[0]
    if name == "s":
        content = content.replace('s="4"', attribute)
    elif name == "dynamic":
        content = content.replace('dynamic="no"', attribute)
    else:
        content += " " + attribute
    with pytest.raises(OpenDriveParseError) as error:
        load(content + "/>")
    assert "/road[@id='r01']/signals/signal[@id='s01']" in error.value.element


def test_missing_signal_and_validity_attributes_fail():
    with pytest.raises(OpenDriveParseError, match="subtype"):
        load(SIGNAL.replace(' subtype="50"', "") + "/>")
    with pytest.raises(OpenDriveParseError, match="toLane"):
        load(SIGNAL + '><validity fromLane="-1"/></signal>')


def test_signal_unknown_content_and_version_features_are_reported():
    result = load(
        SIGNAL + ' temporary="true" extra="x"><semantics><speed/></semantics>'
        '<validity fromLane="-1" toLane="-1" layer="temporary"'
        ' extra="x"><extension/></validity></signal>',
        8,
    )
    codes = [diagnostic.code for diagnostic in result.diagnostics]
    assert codes.count("version-mismatch") == 2
    assert codes.count("unsupported-attribute") == 2
    assert codes.count("unsupported-element") == 2
    assert any(d.element.endswith("/validity/extension") for d in result.diagnostics)
