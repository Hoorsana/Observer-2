"""pylab live plugin for Saleae Logic 1 Legacy.

Requirements:

    - Saleae Logic 1.1.x Legacy
    - saleae-python

The details are loaded from file. File *may* have an extension field `saleae`, which *may* contain the following fields:

* host (str): The host running Logic
* port (int): The port of the socket API
* performance (str): One of the following: 'Full', 'Half', 'Third',
  'Quarter', 'Low'
* grace (float): The grace period used for the recording length
  heuristics (see below)

If so, then these are used to configure the Saleae Logic client. If not,
the following defaults are used: ``host='localhost'``, ``port=10429``,
``performance='Full'``.

The plugin currently suffers from serious restrictions. At most one
Logic Analyzer may be operated at the same time. The time the recording
starts cannot be determined using the Socket API and recording cannot be
stopped manually, which is why the plugin uses a heuristic grace period
to determine when recording starts and ends, thus creating quite long
recordings, even for short tests. Note that this leads to excessive
memory consumption and long wait times _after_ the test.
"""

from __future__ import annotations

import saleae

from pylab.live import live

_logic = None
_grace = None  # Grace period in seconds


def init(info: infos.TestInfo, details: live.Details) -> None:
    total_duration = sum(phase.duration for phase in info.phases)
    args = _parse_args(details)
    _initialize_saleae(**args)


def _parse_args(details: live.Details) -> dict:
    ext_saleae = details.extension.get('saleae')
    if ext_saleae is None:
        return {}
    args = ext_saleae.get('init', {})
    if args.get('performance') is not None:
        args['performance'] = getattr(saleae.PerformanceOption, args['performance'])
    return args


def kill():
    saleae.Saleae.kill_logic(kill_all=True)


def _initialize_saleae(host: str = 'localhost',
                       port: int = 10429,
                       performance: saleae.PerformanceOption = saleae.PerformanceOption.Full,
                       grace: float = 5.0
                      ) -> None:
    """Lazily create global Logic API object.

    Args:
        host: The host running Logic
        port: The port for the socket API
        performance: Performance option for Logic
        grace:
            The grace period for recording length heuristics in seconds
    """
    global _logic
    global _grace
    _logic = saleae.Saleae(host, port)
    _logic.set_performance(performance)
    _grace = grace


def from_id(id: int,
            digital: Optional[list[int]] = None,
            analog: Optional[list[int]] = None,
            sample_rate_digital: int = 0,
            sample_rate_analog: int = 0) -> Device:
    """Create a Logic device from id.

    Args:
        id: The saleae id
        digital: The activate digital channels
        analog: The active analog channels
        sample_rate_digital:
            The minimum digital sample rate in MS/s (0 for "don't care")
        sample_rate_analog:
            The minimum analog sample rate in S/s (0 for "don't care")

    Raises:
        RuntimeError: If ``_initialize`` was not yet called
        StopIteration: If no device with id ``id`` is found
        saleae.ImpossibleSetting:
            If the sample rate settings are invalid
    """
    index, device = next(
        (index, elem) for index, elem
        in enumerate(logic().get_connected_devices())
        if elem.id == id
    )
    _logic.select_active_device(index)

    # Logic and default values based on ``saleae.demo()``.
    if device.type not in {'LOGIC_4_DEVICE', 'LOGIC_DEVICE'}:
        if digital is None:
            digital = [0, 1, 2, 3, 4]
        if analog is None:
            analog = [0, 1]
        _logic.set_active_channels(digital, analog)
    rate = _logic.set_sample_rate_by_minimum(sample_rate_digital, sample_rate_analog)
    assert rate == (sample_rate_digital, sample_rate_analog)

    return Device(device)


def from_config(path: str) -> Device:
    pass


class Device:
    """Handle object for pylab usage."""

    def __init__(self, details: saleae.ConnectedDevice) -> None:
        self._details = details
        self._requests = {}

    @property
    def details(self) -> saleae.ConnectedDevice:
        return self._details

    def _activate(self):
        # TODO Not sure if this is even an option, but maybe multiple
        # devices can run in parallel.
        _logic.select_active_device(self._index())

    def _index(self):
        return _logic.get_connected_devices().index(self._details)

    def _extract_data(self) -> list[...]:  # FIXME Annotation
        self._activate()
        # TODO Do this using the socket API instead of a tempdir
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'data.csv')
            _logic.export_data2(path, delimiter='comma')
            with open(path, 'r') as f:
                reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
                # TODO Read out in chunks (even when using socket API)
                result = list(reader)
        return result  # TODO This needs to be reformatted

    def log_signal(self,
                   channel: tuple[str, int],
                   period: float) -> tuple[live.AbstractFuture, live.AbstractFuture]:
        """Submit a logging request.

        Args:
            channel:
                The type of the channel (``'digital'`` or ``'analog'``)
                and the channel number
            period:
                The logging period in seconds
        """
        del period  # TODO
        self._activate()
        _logic.capture_begin()
        future = Future('result')
        assert channel not in self._requests
        self._requests[channel] = future
        return DelayFuture(self._grace), future

    def end_log_signal(self, channel: tuple[str, int]) -> live.AbstractFuture:
        self._activate  # TODO We need a lock on the _logic API if we want to use two or more logger concurrently!
        assert _logic.capture_stop()
        result = self._extract_data()  # Result must be gotten in a seperate thread, as this will take a while!
        self._requests[channel].set_result(result)


class BaseFuture:

    def __init__(self, what: str) -> None:
        self._what = what
        self._log = report.LogEntry(report.INFO, what)

    def get_result(self) -> None:
        return None

    @property
    def what(self) -> str:
        return self._what

    @property
    def log(self) -> report.LogEntry:
        return self._log


class DelayFuture(BaseFuture):
    """A future for delaying a result for a fixed amount of time."""

    def __init__(self, what: str, delay: float):
        """Args:
            what: The future's description
            delay: The duration of the delay in seconds
        """
        super().__init__(what)
        self._start = time.time()
        self._delay = delay

    def _seconds_until_done(self) -> float:
        return self._start + self._delay - time.time()

    def wait(self, timeout: Optional[float] = None) -> bool:
        if timeout is None:
            wait_for = self._seconds_until_done()
        else:
            wait_for = min(self._seconds_until_done(), timeout)
        time.sleep(self._seconds_until_done)

    def done(self) -> bool:
        return time.time() >= self._start + self._delay


# FIXME This can probably be refactored out. Also: code-duplication?
class Future(BaseFuture):
    """Primitive future object for logging requests."""

    def __init__(self, what: str):
        super().__init__(what)
        self._result = None
        self._done_event = threading.Event()

    def get_result(self) -> Any:
        return self._result

    def set_result(self, result: Any) -> None:
        self._result = result
        self._done_event.set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done_event.wait(timeout)

    def done(self) -> bool:
        return self._done_event.is_set()
