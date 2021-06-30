from __future__ import annotations

from pylab.shared import infos
from pylab._private import utils


def load_details(path: PathLike) -> infos.DetailInfo:
    """Load detail info from ``path``.

    Even on non-UNIX systems, the path must be specified as UNIX
    filesystem path.

    Args:
        path: A filesystem path
    """
    data = utils.yaml_safe_load_from_file(path)
    utils.assert_keys(
        data, {'devices'}, {'connections'},
        'Error when loading details: '
    )
    devices = [_load_device(elem) for elem in data['devices']]
    connections = [infos.ConnectionInfo(**each) for each in data.get('connections', [])]
    return infos.DetailInfo(devices, connections)


def _load_device(data: dict) -> infos.DeviceInfo:
    utils.assert_keys(
        data, {'name'}, {'interface'},
        'Error when loading DeviceInfo: '
    )
    interface = data.get('interface')
    # If `interface` is a string, use that string as filesystem path to
    # a file which contains the interface data.
    if isinstance(interface, str):
        interface_path = _find_instance_path(path, interface)
        data['interface'] = utils.yaml_safe_load_from_file(interface_path)
    return infos.DeviceInfo.from_dict(data)
