# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import serial.tools.list_ports


def create_serial_device_from_serial_number(
    serial_number: str, **kwargs
) -> serial.Serial:
    port = get_address_from_serial_number(serial_number)
    ser = serial.Serial(port=port, **kwargs)
    return ser


def get_address_from_serial_number(serial_number: str) -> str:
    """Get device address from USB serial number.

    Args:
        serial_number: The device's serial number

    Raises:
        StopIteration:
            If there is no device with the specified serial number

    Returns:
        The device's serial port
    """
    comports = serial.tools.list_ports.comports()
    match = next(each for each in comports if each.serial_number == serial_number)
    addr = match.device
    return addr
