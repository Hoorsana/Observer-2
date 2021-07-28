# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import inspect
from typing import Optional
import yaml


def yaml_object(_cls=None,
                loader=yaml.SafeLoader,
                tag: Optional[str] = None,
                replace_from_yaml: bool = True):
    """Turn class into a YAML object with tags and default loader.

    Args:
        _cls:
            Sentinel parameter to check how ``yaml_object`` is called;
            should _never_ be specified by keyword
        loader: The loader of the object
        tag: The yaml tag of the object
        replace_from_yaml: Use default ``from_yaml`` method

    The decorator may be called as ``yaml_object`` or as
    ``yaml_object()``, i.e. with or without parens. The ``_cls``
    parameter is used to detect which behavior is used and should
    *never* be specified by keyword. (This trick is from the
    ``dataclasses`` builtin module.)

    If ``yaml_object`` is used, then default values are used for
    ``loader`` and ``tag``: The default loader is ``yaml.SafeLoader``,
    the default yaml tag of ``class A`` is ``'!A'`` and the default
    ``from_yaml`` unpacks the received dictionary and unpacks into the
    ``__init__`` (see example below).

    Note that the original class is modified when the decorator is
    applied. Don't call ``B = yaml_object(A)`` and then reuse  ``A``!

    Example:
        @yamltools.yaml_object
        class A:
            def __init__(self, value):
                self.value = value
        a = yaml.safe_load('!A\nvalue: -0.12')
        assert a.value == -0.12
    """
    def wrap(cls):
        return _process_class(cls, loader, tag, replace_from_yaml)
    if _cls is None:
        return wrap  # Called with parens.
    return wrap(_cls)  # Called without parens.


def _process_class(cls,
                   loader,
                   tag: Optional[str],
                   replace_from_yaml: bool = True):
    if loader is None:
        loader = yaml.SafeLoader
    if tag is None:
        tag = u'!' + cls.__name__
    cls.yaml_loader = loader
    cls.yaml_tag = tag

    if replace_from_yaml:
        @classmethod
        def from_yaml(cls, loader, node):
            d = loader.construct_mapping(node, deep=True)
            return cls(**d)
        cls.from_yaml = from_yaml

    # Note that ``result`` must be created _after_ setting
    # the ``from_yaml`` methods, the tag and the loader. Otherwise,
    # the meta object will not register the constructor.
    bases = (yaml.YAMLObject,) + inspect.getmro(cls)
    result = type(cls.__name__, bases, cls.__dict__.copy())
    return result
