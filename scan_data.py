"""
Data structures for 3D hydrophone scanning.
"""

from dataclasses import dataclass, field
from typing import Iterator
import json
import numpy as np
from pathlib import Path
from scipy.interpolate import RegularGridInterpolator


@dataclass
class ScanParameters:
    """Parameters defining a 3D scan grid."""

    # Center position
    start_x: float
    start_y: float
    start_z: float

    # Range around center (tuple of (min, max) relative to start)
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    z_range: tuple[float, float]

    # Step size in each axis
    step_x: float
    step_y: float
    step_z: float

    # Timing
    settling_time: float = 0.5  # seconds to wait after move

    # Acquisition parameters
    sample_rate: float = 1e6  # 1 MS/s
    num_samples: int = 10000
    voltage_range: float = 0.1  # 100mV

    def x_positions(self) -> np.ndarray:
        """Get all X positions in the scan."""
        x_min = self.start_x + self.x_range[0]
        x_max = self.start_x + self.x_range[1]
        return np.arange(x_min, x_max + self.step_x / 2, self.step_x)

    def y_positions(self) -> np.ndarray:
        """Get all Y positions in the scan."""
        y_min = self.start_y + self.y_range[0]
        y_max = self.start_y + self.y_range[1]
        return np.arange(y_min, y_max + self.step_y / 2, self.step_y)

    def z_positions(self) -> np.ndarray:
        """Get all Z positions in the scan."""
        z_min = self.start_z + self.z_range[0]
        z_max = self.start_z + self.z_range[1]
        return np.arange(z_min, z_max + self.step_z / 2, self.step_z)

    def grid_positions(self) -> Iterator[tuple[float, float, float]]:
        """
        Generate raster scan path positions.

        Uses bidirectional scanning for efficiency:
        - Z is slowest (outer loop)
        - Y is middle
        - X is fastest (inner loop), alternating direction
        """
        x_pos = self.x_positions()
        y_pos = self.y_positions()
        z_pos = self.z_positions()

        for iz, z in enumerate(z_pos):
            # Alternate Y direction for each Z layer
            y_iter = y_pos if iz % 2 == 0 else y_pos[::-1]
            for iy, y in enumerate(y_iter):
                # Alternate X direction for each Y row
                effective_iy = iy if iz % 2 == 0 else len(y_pos) - 1 - iy
                x_iter = x_pos if effective_iy % 2 == 0 else x_pos[::-1]
                for x in x_iter:
                    yield (x, y, z)

    def total_points(self) -> int:
        """Total number of scan points."""
        return len(self.x_positions()) * len(self.y_positions()) * len(self.z_positions())

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'start_x': self.start_x,
            'start_y': self.start_y,
            'start_z': self.start_z,
            'x_range': list(self.x_range),
            'y_range': list(self.y_range),
            'z_range': list(self.z_range),
            'step_x': self.step_x,
            'step_y': self.step_y,
            'step_z': self.step_z,
            'settling_time': self.settling_time,
            'sample_rate': self.sample_rate,
            'num_samples': self.num_samples,
            'voltage_range': self.voltage_range,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ScanParameters':
        """Create from dictionary."""
        return cls(
            start_x=d['start_x'],
            start_y=d['start_y'],
            start_z=d['start_z'],
            x_range=tuple(d['x_range']),
            y_range=tuple(d['y_range']),
            z_range=tuple(d['z_range']),
            step_x=d['step_x'],
            step_y=d['step_y'],
            step_z=d['step_z'],
            settling_time=d.get('settling_time', 0.5),
            sample_rate=d.get('sample_rate', 1e6),
            num_samples=d.get('num_samples', 10000),
            voltage_range=d.get('voltage_range', 0.1),
        )


@dataclass
class ScanPoint:
    """A single measurement point in a scan."""
    x: float
    y: float
    z: float
    intensity: float  # Peak-to-peak amplitude (primary metric)
    rms: float
    peak_amplitude: float

    def to_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'intensity': self.intensity,
            'rms': self.rms,
            'peak_amplitude': self.peak_amplitude,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ScanPoint':
        return cls(
            x=d['x'],
            y=d['y'],
            z=d['z'],
            intensity=d['intensity'],
            rms=d['rms'],
            peak_amplitude=d['peak_amplitude'],
        )


@dataclass
class ScanResult:
    """Complete results from a 3D scan."""

    parameters: ScanParameters
    points: list[ScanPoint] = field(default_factory=list)

    def add_point(self, point: ScanPoint):
        """Add a measurement point."""
        self.points.append(point)

    def save(self, filepath: str | Path):
        """
        Save scan results to disk.

        Creates two files:
        - {filepath}.json - Metadata and parameters
        - {filepath}.npz - Numpy arrays of data
        """
        filepath = Path(filepath)

        # Save metadata as JSON
        metadata = {
            'parameters': self.parameters.to_dict(),
            'num_points': len(self.points),
        }
        with open(filepath.with_suffix('.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

        # Save data as NPZ
        if self.points:
            x = np.array([p.x for p in self.points])
            y = np.array([p.y for p in self.points])
            z = np.array([p.z for p in self.points])
            intensity = np.array([p.intensity for p in self.points])
            rms = np.array([p.rms for p in self.points])
            peak_amplitude = np.array([p.peak_amplitude for p in self.points])

            np.savez(
                filepath.with_suffix('.npz'),
                x=x, y=y, z=z,
                intensity=intensity,
                rms=rms,
                peak_amplitude=peak_amplitude,
            )

    @classmethod
    def load(cls, filepath: str | Path) -> 'ScanResult':
        """Load scan results from disk."""
        filepath = Path(filepath)

        # Load metadata
        with open(filepath.with_suffix('.json'), 'r') as f:
            metadata = json.load(f)

        parameters = ScanParameters.from_dict(metadata['parameters'])
        result = cls(parameters=parameters)

        # Load data
        npz_path = filepath.with_suffix('.npz')
        if npz_path.exists():
            data = np.load(npz_path)
            for i in range(len(data['x'])):
                result.add_point(ScanPoint(
                    x=float(data['x'][i]),
                    y=float(data['y'][i]),
                    z=float(data['z'][i]),
                    intensity=float(data['intensity'][i]),
                    rms=float(data['rms'][i]),
                    peak_amplitude=float(data['peak_amplitude'][i]),
                ))

        return result

    def to_intensity_grid(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Convert points to 3D intensity grid.

        Returns:
            Tuple of (x_coords, y_coords, z_coords, intensity_3d)
            where intensity_3d[ix, iy, iz] is the intensity at that grid point.
        """
        if not self.points:
            raise ValueError("No points in scan result")

        # Get unique coordinates
        x_coords = np.unique([p.x for p in self.points])
        y_coords = np.unique([p.y for p in self.points])
        z_coords = np.unique([p.z for p in self.points])

        # Create 3D grid
        intensity_3d = np.full((len(x_coords), len(y_coords), len(z_coords)), np.nan)

        # Build index maps
        x_idx = {v: i for i, v in enumerate(x_coords)}
        y_idx = {v: i for i, v in enumerate(y_coords)}
        z_idx = {v: i for i, v in enumerate(z_coords)}

        # Fill grid
        for p in self.points:
            ix = x_idx[p.x]
            iy = y_idx[p.y]
            iz = z_idx[p.z]
            intensity_3d[ix, iy, iz] = p.intensity

        return x_coords, y_coords, z_coords, intensity_3d

    def interpolate(
        self,
        factor: int = 2,
        method: str = 'linear',
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Interpolate scan results to a finer grid.

        Args:
            factor: Upsampling factor (2 = double resolution in each dimension)
            method: Interpolation method ('linear', 'nearest', 'slinear',
                    'cubic', 'quintic', or 'pchip')

        Returns:
            Tuple of (x_coords, y_coords, z_coords, intensity_3d)
            with higher resolution than the original scan.
        """
        x_coords, y_coords, z_coords, intensity_3d = self.to_intensity_grid()

        # Create interpolator from the original grid
        interpolator = RegularGridInterpolator(
            (x_coords, y_coords, z_coords),
            intensity_3d,
            method=method,
            bounds_error=False,
            fill_value=np.nan,
        )

        # Create finer grid
        x_fine = np.linspace(x_coords[0], x_coords[-1], len(x_coords) * factor)
        y_fine = np.linspace(y_coords[0], y_coords[-1], len(y_coords) * factor)
        z_fine = np.linspace(z_coords[0], z_coords[-1], len(z_coords) * factor)

        # Create meshgrid of all fine points
        xx, yy, zz = np.meshgrid(x_fine, y_fine, z_fine, indexing='ij')
        points = np.stack([xx, yy, zz], axis=-1)

        # Interpolate
        intensity_fine = interpolator(points)

        return x_fine, y_fine, z_fine, intensity_fine

    def interpolate_at(
        self,
        points: np.ndarray,
        method: str = 'linear',
    ) -> np.ndarray:
        """
        Interpolate intensity values at arbitrary points.

        Args:
            points: Array of shape (N, 3) with [x, y, z] coordinates
            method: Interpolation method ('linear', 'nearest', 'slinear',
                    'cubic', 'quintic', or 'pchip')

        Returns:
            Array of interpolated intensity values at each point.
        """
        x_coords, y_coords, z_coords, intensity_3d = self.to_intensity_grid()

        interpolator = RegularGridInterpolator(
            (x_coords, y_coords, z_coords),
            intensity_3d,
            method=method,
            bounds_error=False,
            fill_value=np.nan,
        )

        return interpolator(points)
