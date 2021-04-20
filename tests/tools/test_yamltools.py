import pytest
import yaml

from pylab.tools import yamltools


@yamltools.yaml_object
class A:
    def __init__(self, x):
        self.x = x


@yamltools.yaml_object(loader=yaml.BaseLoader, tag='!B')
class B:
    def __init__(self, x):
        self.x = x


def test_yaml_object_without_parens():
    value = 123
    a = yaml.safe_load(
        f"""
        !A
        x: {value}
        """
    )
    assert a.x == value


def test_yaml_object_with_parens():
    value = 'foo'
    b = yaml.load(
        f"""
        !B
        x: {value}
        """,
        Loader=yaml.BaseLoader
    )
    assert b.x == value
