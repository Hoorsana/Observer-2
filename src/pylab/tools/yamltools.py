import inspect
from typing import Optional
import yaml


def yaml_object(loader, tag: Optional[str] = None):
    """Create a decorator which turns a class into a yaml object.

    Args:
        loader: The default loader of the object
        tag: The yaml tag of the object

    The default yaml tag of ``class A`` is ``'!A'``.
    """
    def inner(cls):
        nonlocal tag
        nonlocal loader
        if tag is None:
            tag = u'!' + cls.__name__

        @classmethod
        def from_yaml(cls, loader, node):
            d = loader.construct_mapping(node, deep=True)
            return cls(**d)
        cls.from_yaml = from_yaml
        cls.yaml_tag = tag
        cls.yaml_loader = loader

        # Note that ``result`` must be created _after_ setting
        # the ``from_yaml`` methods, the tag and the loader. Otherwise,
        # the meta object will not register the constructor.
        bases = (yaml.YAMLObject,) + inspect.getmro(cls)
        result = type(cls.__name__, bases, cls.__dict__.copy())
        return result
    return inner


yaml_safe_object = yaml_object(loader=yaml.SafeLoader)
