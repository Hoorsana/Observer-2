<!--
SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH

SPDX-License-Identifier: GPL-3.0-or-later
-->

# pylab-stage

Staging repos for pylab project


## Documentation

To build the documentation run `make sphinx`. The docs are then found in
`docs/build/html/index.html`.


## Technical notes

### Testing

Run `make` to test. Before doing so, make sure that `MATLABPATH`
includes `src/pylab/simulink/_resources` if you want to test
MATLAB/Simulink.

The following targets are available for make:

- `core`
- `tools`
- `cli` (commandline)
- `quick` (runs `core`, `tools`, `cli`)
- `simulink`
- `live`
- `live-flash`
- `example` (`example-adder`)
- `example-adder`
- `example-adder-flash`
- `example-limit`
- `example-limit-flash`
- `saleae`
- `saleae-flash`

Running the `live` and `example-adder` test requires two Arduino Due
boards. The GPIO board must run the [Controllino
implementation](git@bitbucket.org:8tronix/testcenter-arduinodue-gpio.git),
the target must run the source in `arduino/adder` (execute `make flash`
in `arduino/adder`). The serial numbers of these device must be stored
in the environment variables `PYLAB_USB_SERIAL_NUMBER_CONTROLLINO` and
`PYLAB_USB_SERIAL_NUMBER_DEVICE`, respectively. Furthermore, the devices
must be connected as follows: `controllino.DAC0-target.A0`,
`controllino.DAC1-target.A1`, `target.DAC1-controllino.A0` or
`target.DAC0-controllino.A0`.

Another example, `example-limit`, uses the same setup, but requires the
connections `controllino.DAC1-target.A1` and
`target.D40-controllino.D30`. Before running the test, run `make flash`
in `arduino/limit_monitoring`.

Both examples can be run _with flashing_ by calling `example-*-flash`.

Note that `resources/examples/adder/arduino_details.yml` is created from
`arduino_details.yml.in` by entering the USB serial numbers stored in
the environment variables using the `freeze` script.


#### Testing `simulink`

You must set `PYLAB_MATLAB_PATH` equal to the directory of your MATLAB
installation in order for pylab to find the `setup.py` of the MATLAB
engine. If you don't set the variable, the MATLAB engine will not be
installed to the virtual envrionment.

You must also define the environment variable `MATLABPATH` to include
`resources/tests/simulink`.


#### Testing `live.plugin.saleae`

Run `make saleae` to test the saleae component. Before doing so, set the
environment variable `PYLAB_SALEAE_DEVICE_ID_NO_DEVICE` to the id of one
of the four connected devices _that show up when no actual hardware is
connected_ and `PYLAB_SALEAE_DEVICE_ID_LOGIC_PRO_8` to the id of a
Saleae LogicPro 8. You can discover the id using the following script:

```python
import saleae
from tabulat import tabulate

s = saleae.Saleae()
devices = s.get_connected_devices()
data = [(each.name, each.type, each.id) for each in devices]
tab = tabulate(data, headers=['name', 'type', 'id'])
print(tab)
```

Testing requires one Arduino Due Board and a Saleae LogicPro 8. Flash
the Arduino with `arduino/pulsar/` (by running `make flash` in that
directory) and make the following connections: `pulsar.D40-saleae.2`,
`pulsar.DAC1-saleae.3`.

**Beware!** It may be necessary to start Logic Legacy _before_ running
the tests. If you experience blocking or crashes during the tests, try
that.

Note that you need at least commit
`877178f67618cdb3355054eae3666d99dce36aaa` from the saleae-python
repository.


#### Testing `live.plugin.can`

Testing the can plugin requires vcan on Linux. First, load the required
kernel modules and install required packages:

```shell
sudo modprobe vcan
sudo modprobe can-gw
sudo apt-get install can-utils
```

(You may have to load these on every startup!)

Then setup the required vcan devices and network as follows:

```shell
sudo ip link add dev vcan0 type vcan
sudo ip link add dev vcan1 type vcan
sudo ip link add dev vcan2 type vcan
sudo ip link set up vcan0
sudo ip link set up vcan1
sudo ip link set up vcan2
```

Now `ifconfig` should show the newly configured virtual can network.

Finally, configure message forwarding between the two devices:

```shell
sudo cangw -A -s vcan0 -d vcan1 -e
sudo cangw -A -s vcan1 -d vcan2 -e
```

(The middle device `vcan0` will serve as a passthru.)

Run `make can` to test.

~~Furthermore, to run the tests that involve the PCAN-Dongle, you must
install the driver and API:~~

~~* `sudo modprobe peak_usb`?~~
~~* http://www.peak-system.com/fileadmin/media/linux/index.htm > **Driver Package for Proprietary Purposes** > Download PCAN Driver Package; then `sudo apt-get install libpopt-dev`; `make clean all`; `sudo make install`~~
~~* https://www.peak-system.com/PCAN-Basic-Linux.433.0.html; `cd libpcanbasic/pcanbasic`; `make clean`; `make`; `sudo make install`~~

Furthermore, to run the tests that involve the PCAN-Dongle, run:

* sudo modprobe can
* sudo modprobe can-dev
* sudo modprobe can-raw
* sudo modprobe can-bcm
* sudo ip link set can0 type can bitrate 500000
* sudo ip link set up can0

(TODO: Add a script that runs there on every test run.) 


## License

This project is [REUSE 3.0](https://reuse.software) compliant. It is
licensed under GPL-3.0-or-later and CC0-1.0. See `LICENSES/` for
details.


## Contributing

...
