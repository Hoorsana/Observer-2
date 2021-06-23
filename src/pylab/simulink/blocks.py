# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collection of basic block classes.

With the exception of ``Block``, all classes of this module may be
specified as ``type`` argument for MATLAB/Simulink devices. It is not
necessary to specify the full path for these blocks.
"""


from __future__ import annotations

import abc
import json
from typing import Any, Optional

from numpy.typing import ArrayLike

from pylab.simulink import simulink


class AbstractBlock(abc.ABC):
    """Collections of methods called by commands. The blocks may
    implemented these methods."""

    @abc.abstractmethod
    def set_signal(self, channel: str, value: ArrayLike) -> list[str]:
        """Return code snippet for setting output of ``channel`` to
        ``value``.

        See https://www.mathworks.com/help/simulink/slref/constant.html
        for details.

        Args:
            channel: The target port
            value: The new output value
        """
        pass

    @abc.abstractmethod
    def set_signal_ramp(self,
                        channel: str,
                        slope: ArrayLike,
                        start_time: ArrayLike,
                        initial_output: ArrayLike) -> list[str]:
        """Return code snippet for setting the output of ``channel`` to
        a ramp.

        See https://www.mathworks.com/help/simulink/slref/ramp.html for
        details.

        Args:
            channel: The target port
            slope: The slope of the ramp
            start_time: The time at which the ramp engages
            initial_output: The value before the ramp engages
        """
        pass

    @abc.abstractmethod
    def set_signal_sine(self,
                        channel: str,
                        amplitude: ArrayLike,
                        frequency: ArrayLike,
                        phase: Optional[ArrayLike] = 0.0,
                        bias: Optional[ArrayLike] = 0.0) -> list[str]:
        """Return the code snippet for setting the output of ``channel``
        to a sine wave.

        See https://www.mathworks.com/help/simulink/slref/sinewave.html
        for details.

        Args:
            channel: The target port
            amplitude: Amplitude of the wave
            frequency: Frequency of the wave in Hz
            phase: Phase of the wave in radians
            bias: Bias of the wave
        """
        pass

    @abc.abstractmethod
    def log_signal(self,
                   var: str,
                   channel: str,
                   period: Optional[float] = None) -> list[str]:
        """Return the code snippet for logging ``channel``.

        Args:
            var: Workspace variable for storing data
            channel: The target port
            period: The period at which the signal is logged
        """
        pass


class Block(simulink.AbstractBlock):
    """Class representing a Simulink block in the root system.

    Note that the methods ``set_signal_*`` and ``log_signal`` are not
    abstract methods. Every child class of ``Block`` may or may not
    implement any number of these methods and will raise a
    ``NotImplementedError`` if they are called without implementation.
    """

    def __init__(self, name: str, type: str) -> None:
        """Init a block with ``name`` and ``type``.

        Args:
            name: The block's unique name
            type: The block's simulink type, e.g. ``"Sinks/To Workspace"``
        """
        self._name = name
        self._type = type

    @property
    def name(self):
        return self._name

    @property
    def absolute_path(self):
        return simulink.SYSTEM + '/' + self._name

    def setup(self) -> list[str]:
        return [f"add_block('{self._type}', '{self.absolute_path}')"]


class Model(Block):
    """Class representing a `Ports & Subsystems/Model` block.

    The referenced model must satisfy the following requirements:

    - The file of the referenced model must be included in the
      ``MATLABPATH``.
    - All public parameters must be exposed by setting the model's
      ``ParameterArgumentNames`` parameter. See
      [Parameterize a Referenced Model Programmatically](https://www.mathworks.com/help/releases/R2020a/simulink/ug/parameterize-referenced-models-example.html?searchHighlight=Parameterize%20Instances&s_tid=doc_srchtitle)
      for details.
    """

    def __init__(self,
                 name: str,
                 filename: str,
                 params: Optional[dict[str, str]] = None):
        """Initialize the referenced model.

        Args:
            name: The name of the block
            filename: The filename of the referenced model
            params: A dict that maps instance parameters to their initial values

        All instance parameters of the referenced model _must_ occur in
        `params`. Failing to specify a parameter is undefined behavior.
        """
        super().__init__(name, 'simulink/Ports & Subsystems/Model')
        self._filename = filename
        if params is None:
            self._params = {}
        else:
            self._params = params  # Default values of params.

    def setup(self) -> list[str]:
        result = super().setup()
        result.append(
            f"set_param('{self.absolute_path}', 'ModelFile', '{self._filename}')")

        # NOTE We need to set all params at the same time; otherwise,
        # the `inst_spec_params` struct contains invalid values.
        if self._params:
            result += self._update_params()

        return result

    def set_param(self, param: str, value: Any):
        self._params[param] = value
        return self._update_params()

    def _update_params(self) -> list[str]:
        # Return code snippet for updating Simulink instance parameters
        # according to ``self._params``.
        inst_spec_params = 'PYLAB_INST_SPEC_PARAMS'
        keys = 'PYLAB_KEYS'
        values = 'PYLAB_VALUES'
        map_ = 'PYLAB_MAP'

        result = []
        result.append(f"{inst_spec_params} = get_param('{self.absolute_path}', 'InstanceParameters')")  # noqa: E501
        # We're using json.dumps to get double quotes!
        result.append(f"{keys} = {json.dumps(list(self._params.keys()))}")
        result.append(f"{values} = {json.dumps([str(each) for each in self._params.values()])}")  # noqa: E501
        result.append(f"{map_} = containers.Map({keys}, {values})")
        result.append(f"for i = 1:length({inst_spec_params})")
        result.append(f"  {inst_spec_params}(i).Value = {map_}({inst_spec_params}(i).Name)")  # noqa: E501
        result.append(f"end")  # noqa: F541
        result.append(f"set_param('{self.absolute_path}', 'InstanceParameters', {inst_spec_params})")  # noqa: E501

        return result


class MiniGenerator(Model):
    """Lightweight signal generator class with one output."""

    def __init__(self, name: str):
        super().__init__(name, 'pylab_mini_generator.slx',
                         {'constant_value': 0.0, 'amplitude': 1.0, 'bias': 0.0,
                          'frequency': 1.0, 'phase': 0.0, 'slope': 1.0,
                          'start_time': 0.0, 'initial_output': 0.0, 'step_time': 0.0,
                          'initial_value': 0.0, 'final_value': 1.0, 'selection': 3})

    def set_signal(self, channel: Union[str, int], value: ArrayLike) -> list[str]:
        assert channel in {1, '1'}
        result = []
        result += self.set_param('selection', 3)
        result += self.set_param('constant_value', value)
        return result

    def set_signal_ramp(self,
                        channel: str,
                        slope: float,
                        start_time: float,
                        initial_output: float) -> list[str]:
        assert channel in {1, '1'}
        result = []
        result += self.set_param('selection', 1)
        result += self.set_param('slope', slope)
        result += self.set_param('start_time', start_time)
        result += self.set_param('initial_output', initial_output)
        return result

    def set_signal_sine(self,
                        channel: str,
                        amplitude: float,
                        frequency: float,
                        phase: Optional[float] = 0.0,
                        bias: Optional[float] = 0.0) -> list[str]:
        assert channel in {1, '1'}
        result = []
        result += self.set_param('selection', 0)
        result += self.set_param('amplitude', amplitude)
        result += self.set_param('bias', bias)
        result += self.set_param('frequency', frequency)
        result += self.set_param('phase', phase)
        return result

    def set_signal_step(self,
                        channel: str,
                        step_time: float,
                        initial_value: float,
                        final_value: float) -> list[str]:
        assert channel in {1, '1'}
        result = []
        result += self.set_param('selection', 2)
        result += self.set_param('step_time', step_time)
        result += self.set_param('initial_value', initial_value)
        result += self.set_param('final_value', final_value)
        return result


class MiniLogger(Block):
    """Lightweight logger block with one input."""

    def __init__(self, name):
        super().__init__(name, 'simulink/Sinks/To Workspace')

    def log_signal(self,
                   var: str,
                   channel: str,
                   period: Optional[float] = None) -> list[str]:
        assert channel in {1, '1'}
        result = []
        result.append(
            f"set_param('{self.absolute_path}', 'SampleTime', '[{period} 0.0]')")
        result.append(
            f"set_param('{self.absolute_path}', 'VariableName', '{var}')")
        return result
