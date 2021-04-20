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


@pytest.mark.parametrize('input, tag, loader, replace_from_yaml, expected', [
    pytest.param(
        f"""
        !Dummy
        value: foo
        """,
        None,
        yaml.BaseLoader,
        True,
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
        True,
        'foo',
        id='Use non-default tag'
    ),
    pytest.param(
        """
        !Dummy
        value: foo
        """,
        None,
        yaml.SafeLoader,
        False,
        'foobar',
        id='Do not replace from_yalm'
    ),
])
def test_yaml_object(input, tag, loader, replace_from_yaml, expected):
    @yamltools.yaml_object(tag=tag, loader=loader, replace_from_yaml=replace_from_yaml)
    class Dummy:
        def __init__(self, value):
            self.value = value
        @classmethod
        def from_yaml(cls, loader, node):
            d = loader.construct_mapping(node, deep=True)
            d['value'] += 'bar'
            return cls(**d)
    a = yaml.load(input, Loader=loader)
    assert a.value == expected
