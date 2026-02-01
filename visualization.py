"""
3D visualization utilities for scan data.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from scan_data import ScanResult


# Default hydrophone calibration values
DEFAULT_SENSITIVITY_DB = -250  # dB re 1V/µPa
DEFAULT_FREQUENCY_KHZ = 250    # kHz


def voltage_to_kpa(voltage: np.ndarray | float, sensitivity_db: float = DEFAULT_SENSITIVITY_DB) -> np.ndarray | float:
    """
    Convert voltage to pressure in kPa using hydrophone sensitivity.

    Args:
        voltage: Measured voltage (V)
        sensitivity_db: Hydrophone sensitivity in dB re 1V/µPa

    Returns:
        Pressure in kPa
    """
    # Sensitivity in V/µPa: S = 10^(sensitivity_db/20)
    # V = S * P_µPa, so P_µPa = V / S = V * 10^(-sensitivity_db/20)
    # Convert µPa to kPa: 1 kPa = 1e9 µPa
    pressure_upa = voltage * 10 ** (-sensitivity_db / 20)
    pressure_kpa = pressure_upa * 1e-9
    return pressure_kpa


def plot_3d_scatter(
    result: ScanResult,
    figsize: tuple[int, int] = (10, 8),
    cmap: str = 'viridis',
    marker_size: float = 50,
    title: str = "3D Hydrophone Scan",
    sensitivity_db: float = DEFAULT_SENSITIVITY_DB,
) -> plt.Figure:
    """
    Create a 3D scatter plot colored by pressure intensity.

    Args:
        result: Scan result to visualize
        figsize: Figure size
        cmap: Colormap name
        marker_size: Size of scatter points
        title: Plot title
        sensitivity_db: Hydrophone sensitivity in dB re 1V/µPa

    Returns:
        Matplotlib figure
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')

    x = np.array([p.x for p in result.points])
    y = np.array([p.y for p in result.points])
    z = np.array([p.z for p in result.points])
    intensity_v = np.array([p.intensity for p in result.points])
    intensity_kpa = voltage_to_kpa(intensity_v, sensitivity_db)

    scatter = ax.scatter(x, y, z, c=intensity_kpa, cmap=cmap, s=marker_size)

    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    ax.set_title(title)

    fig.colorbar(scatter, ax=ax, shrink=0.6, label='Pressure (kPa)')

    return fig


def plot_slice(
    result: ScanResult,
    plane: str = 'xy',
    position: float | None = None,
    figsize: tuple[int, int] = (8, 6),
    cmap: str = 'viridis',
    title: str | None = None,
    sensitivity_db: float = DEFAULT_SENSITIVITY_DB,
    interpolation: str = 'nearest',
) -> plt.Figure:
    """
    Plot a 2D slice heatmap at a specific position.

    Args:
        result: Scan result to visualize
        plane: Slice plane ('xy', 'xz', or 'yz')
        position: Position along the perpendicular axis (None = middle)
        figsize: Figure size
        cmap: Colormap name
        title: Plot title (auto-generated if None)
        sensitivity_db: Hydrophone sensitivity in dB re 1V/µPa
        interpolation: Interpolation method ('nearest', 'bilinear', 'bicubic', etc.)

    Returns:
        Matplotlib figure
    """
    x_coords, y_coords, z_coords, intensity_3d = result.to_intensity_grid()
    # Convert to kPa
    intensity_3d = voltage_to_kpa(intensity_3d, sensitivity_db)

    plane = plane.lower()
    if plane == 'xy':
        if position is None:
            position = z_coords[len(z_coords) // 2]
        iz = np.argmin(np.abs(z_coords - position))
        data = intensity_3d[:, :, iz].T
        extent = [x_coords[0], x_coords[-1], y_coords[0], y_coords[-1]]
        xlabel, ylabel = 'X (mm)', 'Y (mm)'
        actual_pos = z_coords[iz]
        default_title = f'XY Slice at Z = {actual_pos:.1f} mm'
    elif plane == 'xz':
        if position is None:
            position = y_coords[len(y_coords) // 2]
        iy = np.argmin(np.abs(y_coords - position))
        data = intensity_3d[:, iy, :].T
        extent = [x_coords[0], x_coords[-1], z_coords[0], z_coords[-1]]
        xlabel, ylabel = 'X (mm)', 'Z (mm)'
        actual_pos = y_coords[iy]
        default_title = f'XZ Slice at Y = {actual_pos:.1f} mm'
    elif plane == 'yz':
        if position is None:
            position = x_coords[len(x_coords) // 2]
        ix = np.argmin(np.abs(x_coords - position))
        data = intensity_3d[ix, :, :].T
        extent = [y_coords[0], y_coords[-1], z_coords[0], z_coords[-1]]
        xlabel, ylabel = 'Y (mm)', 'Z (mm)'
        actual_pos = x_coords[ix]
        default_title = f'YZ Slice at X = {actual_pos:.1f} mm'
    else:
        raise ValueError(f"Invalid plane '{plane}'. Use 'xy', 'xz', or 'yz'.")

    fig, ax = plt.subplots(figsize=figsize)

    im = ax.imshow(
        data,
        extent=extent,
        origin='lower',
        aspect='auto',
        cmap=cmap,
        interpolation=interpolation,
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or default_title)

    fig.colorbar(im, ax=ax, label='Pressure (kPa)')

    return fig


def interactive_slice_viewer(
    result: ScanResult,
    plane: str = 'xy',
    figsize: tuple[int, int] = (10, 8),
    cmap: str = 'viridis',
    sensitivity_db: float = DEFAULT_SENSITIVITY_DB,
    interpolation: str = 'nearest',
) -> plt.Figure:
    """
    Create an interactive slice viewer with a slider.

    Args:
        result: Scan result to visualize
        plane: Slice plane ('xy', 'xz', or 'yz')
        figsize: Figure size
        cmap: Colormap name
        sensitivity_db: Hydrophone sensitivity in dB re 1V/µPa
        interpolation: Interpolation method ('nearest', 'bilinear', 'bicubic', etc.)

    Returns:
        Matplotlib figure
    """
    x_coords, y_coords, z_coords, intensity_3d = result.to_intensity_grid()
    # Convert to kPa
    intensity_3d = voltage_to_kpa(intensity_3d, sensitivity_db)

    plane = plane.lower()
    if plane == 'xy':
        axis_coords = z_coords
        axis_label = 'Z'
        extent = [x_coords[0], x_coords[-1], y_coords[0], y_coords[-1]]
        xlabel, ylabel = 'X (mm)', 'Y (mm)'

        def get_slice(idx):
            return intensity_3d[:, :, idx].T
    elif plane == 'xz':
        axis_coords = y_coords
        axis_label = 'Y'
        extent = [x_coords[0], x_coords[-1], z_coords[0], z_coords[-1]]
        xlabel, ylabel = 'X (mm)', 'Z (mm)'

        def get_slice(idx):
            return intensity_3d[:, idx, :].T
    elif plane == 'yz':
        axis_coords = x_coords
        axis_label = 'X'
        extent = [y_coords[0], y_coords[-1], z_coords[0], z_coords[-1]]
        xlabel, ylabel = 'Y (mm)', 'Z (mm)'

        def get_slice(idx):
            return intensity_3d[idx, :, :].T
    else:
        raise ValueError(f"Invalid plane '{plane}'. Use 'xy', 'xz', or 'yz'.")

    # Get global intensity range for consistent colorbar
    vmin = np.nanmin(intensity_3d)
    vmax = np.nanmax(intensity_3d)

    fig, ax = plt.subplots(figsize=figsize)
    plt.subplots_adjust(bottom=0.2)

    initial_idx = len(axis_coords) // 2
    initial_data = get_slice(initial_idx)

    im = ax.imshow(
        initial_data,
        extent=extent,
        origin='lower',
        aspect='auto',
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation=interpolation,
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f'{plane.upper()} Slice at {axis_label} = {axis_coords[initial_idx]:.1f} mm')

    fig.colorbar(im, ax=ax, label='Pressure (kPa)')

    # Add slider
    ax_slider = plt.axes([0.2, 0.05, 0.6, 0.03])
    slider = Slider(
        ax_slider,
        f'{axis_label} (mm)',
        axis_coords[0],
        axis_coords[-1],
        valinit=axis_coords[initial_idx],
    )

    def update(val):
        idx = np.argmin(np.abs(axis_coords - val))
        im.set_data(get_slice(idx))
        ax.set_title(f'{plane.upper()} Slice at {axis_label} = {axis_coords[idx]:.1f} mm')
        fig.canvas.draw_idle()

    slider.on_changed(update)

    # Store slider reference to prevent garbage collection
    fig._slider = slider

    return fig


def plot_all_slices(
    result: ScanResult,
    plane: str = 'xy',
    figsize: tuple[int, int] | None = None,
    cmap: str = 'viridis',
    max_cols: int = 4,
    sensitivity_db: float = DEFAULT_SENSITIVITY_DB,
    interpolation: str = 'nearest',
) -> plt.Figure:
    """
    Plot all slices in a grid.

    Args:
        result: Scan result to visualize
        plane: Slice plane ('xy', 'xz', or 'yz')
        figsize: Figure size (auto if None)
        cmap: Colormap name
        max_cols: Maximum columns in grid
        sensitivity_db: Hydrophone sensitivity in dB re 1V/µPa
        interpolation: Interpolation method ('nearest', 'bilinear', 'bicubic', etc.)

    Returns:
        Matplotlib figure
    """
    x_coords, y_coords, z_coords, intensity_3d = result.to_intensity_grid()
    # Convert to kPa
    intensity_3d = voltage_to_kpa(intensity_3d, sensitivity_db)

    plane = plane.lower()
    if plane == 'xy':
        axis_coords = z_coords
        axis_label = 'Z'
        extent = [x_coords[0], x_coords[-1], y_coords[0], y_coords[-1]]
        xlabel, ylabel = 'X', 'Y'

        def get_slice(idx):
            return intensity_3d[:, :, idx].T
    elif plane == 'xz':
        axis_coords = y_coords
        axis_label = 'Y'
        extent = [x_coords[0], x_coords[-1], z_coords[0], z_coords[-1]]
        xlabel, ylabel = 'X', 'Z'

        def get_slice(idx):
            return intensity_3d[:, idx, :].T
    elif plane == 'yz':
        axis_coords = x_coords
        axis_label = 'X'
        extent = [y_coords[0], y_coords[-1], z_coords[0], z_coords[-1]]
        xlabel, ylabel = 'Y', 'Z'

        def get_slice(idx):
            return intensity_3d[idx, :, :].T
    else:
        raise ValueError(f"Invalid plane '{plane}'. Use 'xy', 'xz', or 'yz'.")

    n_slices = len(axis_coords)
    n_cols = min(n_slices, max_cols)
    n_rows = (n_slices + n_cols - 1) // n_cols

    if figsize is None:
        figsize = (3 * n_cols, 3 * n_rows)

    # Get global intensity range
    vmin = np.nanmin(intensity_3d)
    vmax = np.nanmax(intensity_3d)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, squeeze=False)

    for i, ax in enumerate(axes.flat):
        if i < n_slices:
            data = get_slice(i)
            im = ax.imshow(
                data,
                extent=extent,
                origin='lower',
                aspect='auto',
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
                interpolation=interpolation,
            )
            ax.set_title(f'{axis_label}={axis_coords[i]:.1f}')
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
        else:
            ax.axis('off')

    fig.suptitle(f'{plane.upper()} Slices (Pressure in kPa)', fontsize=14)
    plt.tight_layout()

    return fig
