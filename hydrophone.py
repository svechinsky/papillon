"""
Hydrophone acquisition wrapper around pydwf (Digilent WaveForms).
"""

from dataclasses import dataclass
import numpy as np
import time
from pydwf import DwfLibrary
from pydwf.utilities import openDwfDevice


@dataclass
class AcquisitionResult:
    """Result of a single hydrophone acquisition."""
    samples: np.ndarray
    sample_rate: float
    peak_amplitude: float
    peak_to_peak: float
    rms: float

    @property
    def duration(self) -> float:
        """Duration of acquisition in seconds."""
        return len(self.samples) / self.sample_rate

    @property
    def time_axis(self) -> np.ndarray:
        """Time values for each sample."""
        return np.arange(len(self.samples)) / self.sample_rate


class Hydrophone:
    """
    Hydrophone acquisition interface using Digilent Analog Discovery.

    Wraps the pydwf library for simple acquisition control.
    """

    def __init__(self, channel: int = 0):
        """
        Initialize hydrophone interface.

        Args:
            channel: Analog input channel (0 or 1)
        """
        self.channel = channel
        self._dwf = None
        self._device = None
        self._scope = None
        self._sample_rate = 1e6
        self._num_samples = 10000
        self._voltage_range = 0.1

    def connect(self):
        """Connect to Digilent device."""
        self._dwf = DwfLibrary()
        self._device = openDwfDevice(self._dwf)
        self._scope = self._device.analogIn
        self._apply_configuration()

    def disconnect(self):
        """Disconnect from device."""
        if self._device is not None:
            self._device.close()
            self._device = None
            self._scope = None
            self._dwf = None

    def configure(
        self,
        sample_rate: float | None = None,
        num_samples: int | None = None,
        voltage_range: float | None = None,
    ):
        """
        Configure acquisition parameters.

        Args:
            sample_rate: Samples per second
            num_samples: Number of samples per acquisition
            voltage_range: Input voltage range (peak)
        """
        if sample_rate is not None:
            self._sample_rate = sample_rate
        if num_samples is not None:
            self._num_samples = num_samples
        if voltage_range is not None:
            self._voltage_range = voltage_range

        if self._scope is not None:
            self._apply_configuration()

    def _apply_configuration(self):
        """Apply current configuration to hardware."""
        self._scope.channelEnableSet(self.channel, True)
        self._scope.channelRangeSet(self.channel, self._voltage_range)
        self._scope.frequencySet(self._sample_rate)
        self._scope.bufferSizeSet(self._num_samples)

    def acquire(self) -> AcquisitionResult:
        """
        Perform a single acquisition.

        Returns:
            AcquisitionResult containing samples and computed metrics.
        """
        if self._scope is None:
            raise RuntimeError("Not connected to device")

        # Start acquisition
        self._scope.configure(reconfigure=True, start=True)

        # Wait for completion
        while True:
            status = self._scope.status(read_data_flag=True)
            if status.name == "Done":
                break
            time.sleep(0.001)

        # Read samples
        samples = self._scope.statusData(self.channel, self._num_samples)
        samples = np.array(samples)

        # Compute metrics
        peak_amplitude = float(np.max(np.abs(samples)))
        peak_to_peak = float(np.max(samples) - np.min(samples))
        rms = float(np.sqrt(np.mean(samples ** 2)))

        return AcquisitionResult(
            samples=samples,
            sample_rate=self._sample_rate,
            peak_amplitude=peak_amplitude,
            peak_to_peak=peak_to_peak,
            rms=rms,
        )

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._device is not None
