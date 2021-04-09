.. SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
.. 
.. SPDX-License-Identifier: GPL-3.0-or-later


pylab.simulink developer notes
==============================

The driver creates an .M files ahead-of-time which holds all relevant
data and is executed by MATLAB. All results are saved to the workspace
and may be gathered from there.


Design philosophy
+++++++++++++++++

* Never modify a user's model or create a new model with the exception of the root sytem

* Avoid using the MATLAB engine as much as possible; do everything in
  Python to keep code clean and testable


Test object
+++++++++++

The `simulink.Test` object represents an ``.M`` file; the content of the
``.M`` file is determined by the specified test data and details.
Running the test by hand will most likely fail due to missing resources
(when calling `Test.execute()`, the test file and the required resources
are moved to a tempdir and executed there).

The test file is responsible for creating the root system, running the
main loop and logging test execution errors. An example of a test file
with comments may be found at the end of this file.


Root system
+++++++++++++++

The test setup is deployed in a Simulink system, the *root system*. The
system is called `simulink.SYSTEM`.


Main loop
+++++++++++++

The simulation is run using a stop-and-go technique in the *main loop*.
The simulation is run until a command must be executed:

.. code-block:: MATLAB

  PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '0.4')

In this case, a command is executed at time ``0.4``. The execution of the
command is the following rather complicated pattern used to set instance
parameters. In this case, the effect is that a signal is set.

.. code-block:: MATLAB

    PYLAB_WHAT = "CommandInfo(time=0.4, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]

(For details on the usage of ``PYLAB_LOGBOOK``, see below.)

The state of the simulation was saved in an operating point when it was
stopped at 0.4; for the next iteration of the loop, the state is
restored and the simulation continued until the next command is up for
execution.


Logging results
+++++++++++++++

Logged results are saved in the workspace at the end of the test in a
workspace variable called ``{info.target}PYLAB_DOT{info.signal}``, where ``info`` is
the ``infos.LoggingInfo`` used to describe the logging request. The driver
implements this by defining the workspace variable ``OUTPUT`` as empty array and
appending the ``simout`` structures returned after each section of the
simulation:

At the end of the test, the ``timeseries`` contents of the items
of ``OUTPUT`` are concatenated using the function ``pylab_extract`` and then
saved in workspace variables of the above form.


Error logging
+++++++++++++

Logbook messages are saved in the workspace variable ``LOGBOOK``. In order
to catch errors without crashing MATLAB, the entire main loop is placed
in a ``try`` block (see ``simulink._head``). If an error occurs, the ``catch``
block (see ``simulink._catch_block``) appends the error message to
``LOGBOOK``.

In order to pinpoint which pylab command failed, the ``WHAT`` variable
should always be set before executing the corresponding MATLAB
statement. If the command fails, the content of ``WHAT`` is then added to
the error message. This leads to the following pattern when executing
commands (see ``simulink.Command.execute``):

.. code-block:: MATLAB

   try
     PYLAB_WHAT = "command details"
     %{ execute MATLAB statements of command %}  
     PYLAB_LOGBOOK = [PYLAB_LOGBOOK; %{ something involving PYLAB_WHAT %}]  % Add info to logbook; won't happen if command execution fails.
     %{ ... %}
   catch
     %{ add PYLAB_WHAT to logbook %}
   end


Workspace variables
+++++++++++++++++++

The driver make use of the global workspace to store logging results.

All workspace variables containing ``PYLAB`` or ``pylab`` are *reserved*
by the core driver, with the exception of string matching
``PYLAB_EXTENSION_*``, which are reserved for registered extensions. If a
user defines a workspace variable reserved by the driver, the result is
undefined behavior.

Extensions should use ``PYLAB_EXTENSION_*`` to store workspace variables.
We further suggest namespacing them by using
``PYLAB_EXTENSION_PROJECT_*``.


Resource files
++++++++++++++

All resource files are placed in ``pylab.simulink._resources``. In order
to use ``.M`` in a test, add the filenames to the list ``simulink.TOOLBOX``.


Test file example
+++++++++++++++++

.. code-block:: MATLAB

  % Initialize variables for logging
  PYLAB_LOGBOOK = []
  PYLAB_OUTPUT = []
  PYLAB_WHAT = ""
  try
    % Initialize root system; setup blocks (some require quite alot of
    % code due to usage of instance parameters.
    PYLAB_WHAT = "Initializing root system"
    new_system('PYLAB_SYSTEM')
    set_param('PYLAB_SYSTEM', ...
              'SaveFinalState', 'on', ...
              'FinalStateName', 'PYLAB_OPERATING_POINT', ...
              'SaveOperatingPoint', 'on')
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    add_block('simulink/Ports & Subsystems/Model', 'PYLAB_SYSTEM/monitor')
    set_param('PYLAB_SYSTEM/monitor', 'ModelFile', 'limit_monitoring.slx')
    add_block('simulink/Ports & Subsystems/Model', 'PYLAB_SYSTEM/gpio')
    set_param('PYLAB_SYSTEM/gpio', 'ModelFile', 'pylab_mini_generator.slx')
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    add_block('simulink/Sinks/To Workspace', 'PYLAB_SYSTEM/logger')
    add_line('PYLAB_SYSTEM', 'gpio/1', 'monitor/1', 'autorouting', 'on')
    add_line('PYLAB_SYSTEM', 'monitor/1', 'logger/1', 'autorouting', 'on')
    PYLAB_WHAT = "LoggingInfo(target='monitor', signal='result', period=0.1, description='')"
    set_param('PYLAB_SYSTEM/logger', 'SampleTime', '[0.1 0.0]')
    set_param('PYLAB_SYSTEM/logger', 'VariableName', 'monitorPYLABDOTresult')
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_WHAT = "CommandInfo(time=0.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': -100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]

    % Main loop - first iteration
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '0.4')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.4, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    % Main loop - second iteration, etc.
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '0.6')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.6, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 0}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '1.4')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.4, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '1.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': -100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '1.6')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.6, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 0}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '2.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': -100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '2.4')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.4, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 100}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '2.6')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.6, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 0}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["100.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '3.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 81}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["0.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["81.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '4.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=1.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 79}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["81.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["79.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '5.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=0.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': -95}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["79.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-95.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '6.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_WHAT = "CommandInfo(time=1.0, command='CmdSetSignal', target='monitor', data={'signal': 'temperature', 'value': 95}, description='')"
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["-95.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_INST_SPEC_PARAMS = get_param('PYLAB_SYSTEM/gpio', 'InstanceParameters')
    PYLAB_KEYS = ["constant_value", "amplitude", "bias", "frequency", "phase", "slope", "start_time", "initial_output", "step_time", "initial_value", "final_value", "selection"]
    PYLAB_VALUES = ["95.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "1.0", "3"]
    PYLAB_MAP = containers.Map(PYLAB_KEYS, PYLAB_VALUES)
    for i = 1:length(PYLAB_INST_SPEC_PARAMS)
      PYLAB_INST_SPEC_PARAMS(i).Value = PYLAB_MAP(PYLAB_INST_SPEC_PARAMS(i).Name)
    end
    set_param('PYLAB_SYSTEM/gpio', 'InstanceParameters', PYLAB_INST_SPEC_PARAMS)
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""info"", ""data"": {}}"]
    PYLAB_SIMOUT = sim('PYLAB_SYSTEM', 'StopTime', '7.0')
    PYLAB_OPERATING_POINT = PYLAB_SIMOUT.PYLAB_OPERATING_POINT
    set_param('PYLAB_SYSTEM', 'LoadInitialState', 'on', ...
              'InitialState', 'PYLAB_OPERATING_POINT')
    PYLAB_OUTPUT = [PYLAB_OUTPUT PYLAB_SIMOUT]
    PYLAB_OUTPUT_monitorPYLABDOTresult = pylab_extract(PYLAB_OUTPUT, 'monitorPYLABDOTresult')
    % End main loop
  catch PYLAB_ERROR
    % Error handling
    data = "{"
    identifier = strrep(PYLAB_ERROR.identifier, '"', '''')
    data = data + """identifier"": """ + identifier + """, "
    message = strrep(PYLAB_ERROR.message, '"', '''')
    data = data + """message"": """ + message + """, "
    data = data + """stack"": ["
    for PYLAB_INDEX0 = 1:length(PYLAB_ERROR.stack)
      item = PYLAB_ERROR.stack(PYLAB_INDEX0)
      data = data + "{"
      data = data + """file"": """ + item.file + """, "
      data = data + """name"": """ + item.name + """, "
      data = data + """line"": """ + item.line + """"
      data = data + "}"
      if PYLAB_INDEX0 ~= length(PYLAB_ERROR.stack)
        data = data + ", "
      end
    end
    data = data + "]"
    data = data + "}"
    PYLAB_LOGBOOK = [PYLAB_LOGBOOK; ...
      "{""what"": """ + PYLAB_WHAT + """, ""severity"": ""panic"", ""data"": " + data + "}"]
  end
