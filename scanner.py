"""
3D Hydrophone Scanner - Main orchestration class.
"""

import time
from typing import Callable

from flsun_control import FLSunPrinter
from hydrophone import Hydrophone
from scan_data import ScanParameters, ScanResult, ScanPoint


class Scanner:
    """
    Orchestrates 3D hydrophone scanning by coordinating printer movement
    with hydrophone acquisition.
    """

    def __init__(
        self,
        printer_port: str,
        printer_baudrate: int = 115200,
        hydrophone_channel: int = 0,
    ):
        """
        Initialize scanner.

        Args:
            printer_port: Serial port for FLSUN printer
            printer_baudrate: Baud rate for printer communication
            hydrophone_channel: Analog input channel for hydrophone
        """
        self._printer = FLSunPrinter(printer_port, printer_baudrate)
        self._hydrophone = Hydrophone(hydrophone_channel)
        self._abort_requested = False

    def connect(self):
        """Connect to both printer and hydrophone."""
        if not self._printer.connect():
            raise RuntimeError("Failed to connect to printer")
        try:
            self._hydrophone.connect()
        except Exception as e:
            self._printer.disconnect()
            raise RuntimeError(f"Failed to connect to hydrophone: {e}")

    def disconnect(self):
        """Disconnect from printer and hydrophone."""
        self._hydrophone.disconnect()
        self._printer.disconnect()

    def home(self):
        """Home the printer."""
        self._printer.home()

    def move_to(self, x: float, y: float, z: float, feedrate: int = 3000):
        """Move printer to absolute position."""
        self._printer.move(x=x, y=y, z=z, feedrate=feedrate)

    def scan(
        self,
        params: ScanParameters,
        progress_callback: Callable[[int, int, ScanPoint], None] | None = None,
        home_before: bool = False,
        home_after: bool = False,
    ) -> ScanResult:
        """
        Execute a full 3D scan.

        Args:
            params: Scan parameters defining the grid
            progress_callback: Called after each point with (current, total, point)
            home_before: Home printer before starting scan
            home_after: Return to home position after scan

        Returns:
            ScanResult containing all measured points
        """
        self._abort_requested = False

        # Configure hydrophone
        self._hydrophone.configure(
            sample_rate=params.sample_rate,
            num_samples=params.num_samples,
            voltage_range=params.voltage_range,
        )

        # Home if requested
        if home_before:
            self.home()

        result = ScanResult(parameters=params)
        total_points = params.total_points()

        # Scan through all positions
        for i, (x, y, z) in enumerate(params.grid_positions()):
            if self._abort_requested:
                break

            # Move to position
            self.move_to(x, y, z)

            # Wait for settling
            time.sleep(params.settling_time)

            # Acquire data
            acq = self._hydrophone.acquire()

            # Create scan point (intensity = peak-to-peak amplitude)
            point = ScanPoint(
                x=x,
                y=y,
                z=z,
                intensity=acq.peak_to_peak,
                rms=acq.rms,
                peak_amplitude=acq.peak_amplitude,
            )
            result.add_point(point)

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, total_points, point)

        # Home after if requested
        if home_after and not self._abort_requested:
            self.home()

        return result

    def abort(self):
        """Request abort of scan in progress."""
        self._abort_requested = True

    @property
    def is_connected(self) -> bool:
        """Check if both printer and hydrophone are connected."""
        return (
            self._printer.serial is not None
            and self._printer.serial.is_open
            and self._hydrophone.is_connected
        )
