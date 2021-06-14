import pytest

from pylab._private import rogueplugin


@pytest.fixture
def configure():
    # TODO
    rogueplugin.init(info, details)
    rogueplugin.post_init('unused', 'unused', 'unused')
    yield
    rogueplugin.reset()


def test_minimal(configure):
    pass
