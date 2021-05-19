import os
import time

import pytest

from pylab.core import infos
from pylab.core import workflow
from pylab.live import live
from pylab.live.plugin.saleae import logic


def test_basic(pulsar, details):
    logic.init(pulsar, details)
    time.sleep(0.1)


@pytest.mark.skip
def test_functional(pulsar, details):
    report = workflow.run(live, pulsar, details)
    print(report)
    print([k for k in report.results])


@pytest.fixture
def pulsar():
    return infos.TestInfo(
        [
            infos.TargetInfo(
                name='pulsar',
                signals=[
                    infos.SignalInfo(
                        name='analog',
                        flags=['output', 'analog'],
                        min=0,
                        max=200
                    ),
                    infos.SignalInfo(
                        name='digital',
                        flags=['output', 'digital'],
                        min=0,
                        max=1
                    ),
                ],
            )
        ],
        [
            infos.LoggingInfo(target='pulsar', signal='analog', period=None),
            infos.LoggingInfo(target='pulsar', signal='digital', period=None),
        ],
        [infos.PhaseInfo(duration=1.0, commands=[])]
    )


@pytest.fixture
def details():
    return live.Details(
        devices=[
            live.DeviceDetails(
                name='pulsar',
                module='pylab.live.live',
                type='UsbSerialDevice.from_serial_number',
                data={'serial_number': os.environ['PYLAB_USB_SERIAL_NUMBER_DEVICE']},
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'analog',
                            'DAC1',
                            min=0, max=255,
                            flags=['output', 'analog']
                        ),
                        infos.PortInfo(
                            'sum',
                            'D45',
                            min=0, max=1,
                            flags=['output', 'digital']
                        ),
                    ]
                )
            ),
            live.DeviceDetails(
                name='logger',
                module='pylab.live.plugin.saleae.logic',
                type='Device.from_id',
                data={
                    'id': os.environ['PYLAB_SALEAE_DEVICE_ID_LOGIC_PRO_8'],
                    'digital': [2],
                    'analog': [3],
                    'sample_rate_digital': 100,
                    'sample_rate_analog': 100
                },
                interface=infos.ElectricalInterface(
                    ports=[
                        infos.PortInfo(
                            'analog',
                            ('analog', 3),
                            min=0, max=255,
                            flags=['input', 'analog']
                        ),
                        infos.PortInfo(
                            'digital',
                            ('digital', 2),
                            min=0, max=1,
                            flags=['input', 'digital']
                        )
                    ]
                )
            )
        ],
        connections=[
            infos.ConnectionInfo(
                sender='pulsar', sender_port='analog',
                receiver='logger', receiver_port=('analog', 3)
            ),
            infos.ConnectionInfo(
                sender='pulsar', sender_port='digital',
                receiver='logger', receiver_port=('digita', 2)
            ),
        ],
        extension={
            'saleae': {
                'init': {
                    'host': 'localhost',
                    # 'performance': 'Full',
                    'port': 10429,
                    'grace': 5.0
                }
            }
        }
    )
