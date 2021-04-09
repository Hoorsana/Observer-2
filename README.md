<!--
SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH

SPDX-License-Identifier: GPL-3.0-or-later
-->

# pylab-stage

Staging repos for pylab project


## Technical notes

### Testing

`all`, `core`, `quick`, ...

Run `make` to test. Before doing so, make sure that `MATLABPATH` includes `src/pylab/simulink/_resources` if you want to test MATLAB/Simulink.

Furthermore, if you must set `PYLAB_MATLAB_PATH` equal to the directory of your MATLAB installation in order for pylab to find the `setup.py` of the MATLAB engine. If you don't set the variable, the
MATLAB engine will not be installed.

Running the `live` and `example` test requires two Arduino Due boards.
The GPIO board must run the [Controllino
implementation](git@bitbucket.org:8tronix/testcenter-arduinodue-gpio.git),
the target must run the source in `arduino/adder`. The serial numbers of
these device must be stored in the environment variables
`PYLAB_USB_SERIAL_NUMBER_CONTROLLINO` and
`PYLAB_USB_SERIAL_NUMBER_DEVICE`, respectively. Furthermore, the devices
must be connected as follows: `controllino.DAC0-target.A0`,
`controllino.DAC1-target.A1`, `target.DAC0-controllino.A0`.


### Complex tasks

* Fix the range-narrowing algorithm! Some examples that illustrate the
  problem:

  - If DAC0->A0 and the (electrical) range of DAC0 is wider than A0, say
    [0, 5] vs. [2, 3], and A0 has a physical range of [0, 100], then all
    physical values can be mapped. However, a value of 25 should be
    represented by a value of 2.25, not 1.25.

  - If DAC0->A0 and the (electrical) ranges of DAC0 and A0 are [0, 5]
    and [3, 6], then physical values at the upper end of the range
    _cannot_ be mapped and a `LogicError` should be raised.

  Another example to illustrate the problem from the Arduino Due:

  ```
    DACX                                          AX
  { electrical range: [0, 255]          }       { electrical range: [0, 1023] }
  { actual electrical range: [168, 852] } ----> {                             }
  { voltage: 0.55V-2.75V                } ----> { voltage: 0V-3.3V            }
  { physical range: [0, 1023]           }       { physical range: [0, 1023]   }
  ```

  (Physical range taken for simplicity.) What `min`, `max` do we specify
  in the `PortInfo` objects? Possible solutions:

  - Limit the range on the left to [0, 255] and to [168, 852] on the
    right.

  - Set the range of both to whatever you want (the values don't mean
    anything specific per se), and then transform the values inside the
    driver or the Arduino Due device to the correct range.

  - Provide the volatages in addition to the electrical values


## License

This project is [REUSE 3.0](https://reuse.software) compliant. It is
licensed under GPL-3.0-or-later and CC0-1.0. See `LICENSES/` for
details.


## Contributing

...
