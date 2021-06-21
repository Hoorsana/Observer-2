import pytest


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'slow: mark test as slow'
    )
    config.addinivalue_line(
        'markers', 'dependency(module): mark test as depending on an external module'
    )
