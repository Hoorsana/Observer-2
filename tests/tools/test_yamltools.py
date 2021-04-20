import pytest
import yaml

from pylab.tools import yamltools


def test_yaml_object_no_parens():
    @yamltools.yaml_object
    class A:
        def __init__(self, x):
            self.x = x
    value = -0.12
    a = yaml.safe_load(
        f"""
        !A
        x: {value}
        """
    )
    assert a.x == value


@pytest.mark.parametrize('input, tag, loader, expected', [
    pytest.param(
        f"""
        !Dummy
        value: foo
        """,
        None,
        yaml.BaseLoader,
        'foo',
        id='Use BaseLoader instead of SafeLoader'
    ),
    pytest.param(
        """
        !tag
        value: foo
        """,
        '!tag',
        yaml.SafeLoader,
        'foo',
        id='Use non-default tag'
    ),
])
def test_yaml_object(input, tag, loader, expected):
    @yamltools.yaml_object(tag=tag, loader=loader)
    class Dummy:
        def __init__(self, value):
            self.value = value
    a = yaml.load(input, Loader=loader)
    assert a.value == expected
