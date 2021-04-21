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

The following targets are available for make: `core`, `tools`, `cli`
(commandline), `quick` (runs `core`, `tools`, `cli`), `simulink`,
`live`, `example`. The `example` target runs the `adder` example on the
simulink driver (if available) and the live driver using the controllino
plugin.

You must set `PYLAB_MATLAB_PATH` equal to the directory of your MATLAB
installation in order for pylab to find the `setup.py` of the MATLAB
engine. If you don't set the variable, the MATLAB engine will not be
installed along with the other modules.

Running the `live` and `example` test requires two Arduino Due boards.
The GPIO board must run the [Controllino
implementation](git@bitbucket.org:8tronix/testcenter-arduinodue-gpio.git),
the target must run the source in `arduino/adder`. The serial numbers of
these device must be stored in the environment variables
`PYLAB_USB_SERIAL_NUMBER_CONTROLLINO` and
`PYLAB_USB_SERIAL_NUMBER_DEVICE`, respectively. Furthermore, the devices
must be connected as follows: `controllino.DAC0-target.A0`,
`controllino.DAC1-target.A1`, `target.DAC0-controllino.A0`.


## License

This project is [REUSE 3.0](https://reuse.software) compliant. It is
licensed under GPL-3.0-or-later and CC0-1.0. See `LICENSES/` for
details.


## Contributing

...
