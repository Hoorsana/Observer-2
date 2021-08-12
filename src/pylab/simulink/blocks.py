# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collection of basic block classes.

With the exception of ``Block``, all classes of this module may be
specified as ``type`` argument for MATLAB/Simulink devices. It is not
necessary to specify the full path for these blocks.
"""


from __future__ import annotations

import uuid
import abc
import json
from typing import Any, Optional

from pylab.core.typing import ArrayLike
from pylab.simulink import simulink


def _random_id() -> str:
    """Create a random id.

    We use this to avoid collisions between certain MATLAB/Simulink
    parameter names.
    """
    id_ = str(uuid.uuid4())
    id_ = id_.replace("-", "_")
    id_ = "pylab_" + id_
    return id_


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
    def set_signal_ramp(
        self,
        channel: str,
        slope: ArrayLike,
        start_time: ArrayLike,
        initial_output: ArrayLike,
    ) -> list[str]:
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
    def set_signal_sine(
        self,
        channel: str,
        amplitude: ArrayLike,
        frequency: ArrayLike,
        phase: Optional[ArrayLike] = 0.0,
        bias: Optional[ArrayLike] = 0.0,
    ) -> list[str]:
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
    def log_signal(
        self, var: str, channel: str, period: Optional[float] = None
    ) -> list[str]:
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
        return simulink.SYSTEM + "/" + self._name

    def setup(self) -> list[str]:
        return [f"add_block('{self._type}', '{self.absolute_path}')"]

    # def get_path_of_port(self, port: Union[int, str], direction: str) -> str:
    #     """Return the path of the specified port.

    #     Args:
    #         port: The id of the port
    #         direction: 'in' or 'out'

    #     This allows a block to define certain abstractions for making
    #     connections. For example, the block may now consist of multiple
    #     (Simulink) blocks and a re-implementation of get_path_of_port
    #     may be used to define which port are exposed, and in what role.
    #     """


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

    def __init__(
        self, name: str, filename: str, params: Optional[dict[str, str]] = None
    ):
        """Initialize the referenced model.

        Args:
            name: The name of the block
            filename: The filename of the referenced model
            params: A dict that maps instance parameters to their initial values

        All instance parameters of the referenced model _must_ occur in
        `params`. Failing to specify a parameter is undefined behavior.
        """
        super().__init__(name, "simulink/Ports & Subsystems/Model")
        self._filename = filename
        if params is None:
            self._params = {}
        else:
            self._params = params  # Default values of params.

    def setup(self) -> list[str]:
        result = super().setup()
        result.append(
            f"set_param('{self.absolute_path}', 'ModelFile', '{self._filename}')"
        )

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
        inst_spec_params = "PYLAB_INST_SPEC_PARAMS"
        keys = "PYLAB_KEYS"
        values = "PYLAB_VALUES"
        map_ = "PYLAB_MAP"

        result = []
        result.append(
            f"{inst_spec_params} = get_param('{self.absolute_path}', 'InstanceParameters')"
        )  # noqa: E501
        # We're using json.dumps to get double quotes!
        result.append(f"{keys} = {json.dumps(list(self._params.keys()))}")
        result.append(
            f"{values} = {json.dumps([str(each) for each in self._params.values()])}"
        )  # noqa: E501
        result.append(f"{map_} = containers.Map({keys}, {values})")
        result.append(f"for i = 1:length({inst_spec_params})")
        result.append(
            f"  {inst_spec_params}(i).Value = {map_}({inst_spec_params}(i).Name)"
        )  # noqa: E501
        result.append(f"end")  # noqa: F541
        result.append(
            f"set_param('{self.absolute_path}', 'InstanceParameters', {inst_spec_params})"
        )  # noqa: E501

        return result


class MiniGenerator(Model):
    """Lightweight signal generator class with one output."""

    def __init__(self, name: str):
        super().__init__(
            name,
            "pylab_mini_generator.slx",
            {
                "constant_value": 0.0,
                "amplitude": 1.0,
                "bias": 0.0,
                "frequency": 1.0,
                "phase": 0.0,
                "slope": 1.0,
                "start_time": 0.0,
                "initial_output": 0.0,
                "step_time": 0.0,
                "initial_value": 0.0,
                "final_value": 1.0,
                "selection": 3,
            },
        )

    def set_signal(self, channel: Union[str, int], value: ArrayLike) -> list[str]:
        assert channel in {1, "1"}
        result = []
        result += self.set_param("selection", 3)
        result += self.set_param("constant_value", value)
        return result

    def set_signal_ramp(
        self, channel: str, slope: float, start_time: float, initial_output: float
    ) -> list[str]:
        assert channel in {1, "1"}
        result = []
        result += self.set_param("selection", 1)
        result += self.set_param("slope", slope)
        result += self.set_param("start_time", start_time)
        result += self.set_param("initial_output", initial_output)
        return result

    def set_signal_sine(
        self,
        channel: str,
        amplitude: float,
        frequency: float,
        phase: Optional[float] = 0.0,
        bias: Optional[float] = 0.0,
    ) -> list[str]:
        assert channel in {1, "1"}
        result = []
        result += self.set_param("selection", 0)
        result += self.set_param("amplitude", amplitude)
        result += self.set_param("bias", bias)
        result += self.set_param("frequency", frequency)
        result += self.set_param("phase", phase)
        return result

    def set_signal_step(
        self, channel: str, step_time: float, initial_value: float, final_value: float
    ) -> list[str]:
        assert channel in {1, "1"}
        result = []
        result += self.set_param("selection", 2)
        result += self.set_param("step_time", step_time)
        result += self.set_param("initial_value", initial_value)
        result += self.set_param("final_value", final_value)
        return result


class MiniLogger(Block):
    """Lightweight logger block with one input."""

    def __init__(self, name):
        super().__init__(name, "simulink/Sinks/To Workspace")

    def setup(self):
        result = super().setup()
        # Use ``_random_id`` to avoid collisions between two or more
        # blocks that use the To Workspace block. In fact, without the
        # use of a random id, the following problem occurs: The
        # ``VariableName`` parameter is set in the ``log_signal``
        # function, which may not be called with the ``MiniLogger`` is
        # not connected to another device. Thus, two or more unconnected
        # ``MiniLogger`` blocks will have the same ``VariableName``,
        # resulting in a MATLAB/Simulink error.
        result.append(
            f"set_param('{self.absolute_path}', 'VariableName', '{_random_id()}')"
        )
        return result

    def log_signal(
        self, var: str, channel: str, period: Optional[float] = None
    ) -> list[str]:
        assert channel in {1, "1"}
        result = []
        if period is not None:
            result.append(
                f"set_param('{self.absolute_path}', 'SampleTime', '[{period} 0.0]')"
            )
        result.append(f"set_param('{self.absolute_path}', 'VariableName', '{var}')")
        return result


class Subsystem(Block):
    def __init__(
        self, name: str, blocks: dict[str, str], lines: list[tuple[str, str]]
    ) -> None:
        """Args:
        name: The block name
        blocks:
            The subsystem's blocks, specified in the following
            format: ``{name: type, ...}``
        lines:
            The subsystems's lines (connections), specified in the
            following format:
            ``[('src_name/src_port', 'dst_name/dst_port')]``

        """
        super().__init__(name, "simulink/Ports & Subsystems/Subsystem")
        self._blocks = blocks
        self._lines = lines

    def setup(self) -> list[str]:
        result = super().setup()
        # Delete the default blocks.
        result.append(f"delete_block('{self.absolute_path}/In1')")
        result.append(f"delete_block('{self.absolute_path}/Out1')")
        for name, type_ in self._blocks.items():
            result.append(f"add_block('{type_}', '{self.absolute_path}/{name}')")
        for elem in self._lines:
            result.append(f"add_line('{self.absolute_path}', '{elem[0]}', '{elem[1]}')")
        return result


class PassthruLogger(Subsystem):
    """Logger block with one input and a passthru output."""

    def __init__(self, name):
        super().__init__(
            name,
            {
                "in": "simulink/Sources/In1",
                "out": "simulink/Sinks/Out1",
                "to_workspace": "simulink/Sinks/To Workspace",
            },
            [("in/1", "out/1"), ("in/1", "to_workspace/1")],
        )

    def setup(self) -> list[str]:
        result = super().setup()
        # Use ``_random_id`` to avoid collisions between two or more
        # blocks that use the To Workspace block. See
        # ``MiniLogger.setup`` for details.
        path = self.absolute_path + "/to_workspace"
        result.append(f"set_param('{path}', 'VariableName', '{_random_id()}')")
        return result

    def log_signal(
        self, var: str, channel: str, period: Optional[float] = None
    ) -> list[str]:
        assert channel in {1, "1"}
        result = []
        path = self.absolute_path + "/to_workspace"
        result.append(f"set_param('{path}', 'VariableName', '{var}')")
        if period is not None:
            result.append(f"set_param('{path}', 'SampleTime', '[{period} 0.0]')")
        return result
