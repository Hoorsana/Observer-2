import pytest
import yaml

from pylab.tools import yamltools


@pytest.fixture
def cls():
    @yamltools.yaml_object
    class A:
        def __init__(self, x):
            self.x = x
    @yamltools.yaml_object
    class B:
        def __init__(self, x):
            self.x = x


def test_yaml_object(cls):
    value = 123
    a = yaml.safe_load(
        f"""
        !A
        x: {value}
        """
    )
    assert a.x == 123
