#!/usr/bin/env python3
"""
Papillion - 3D Hydrophone Scanning System

CLI interface for coordinating FLSUN printer positioning with
Digilent hydrophone data acquisition.
"""

import argparse
import sys
from pathlib import Path

import yaml

from scan_data import ScanParameters, ScanResult
from scanner import Scanner
from visualization import (
    plot_3d_scatter,
    plot_slice,
    interactive_slice_viewer,
    plot_all_slices,
)


DEFAULT_CONFIG = {
    'device': {
        'printer_port': '/dev/ttyUSB0',
        'printer_baud': 115200,
        'hydrophone_channel': 0,
    },
    'position': {
        'x': 0,
        'y': 0,
        'z': 100,
    },
    'range': {
        'x': 10,  # ±mm
        'y': 10,
        'z': 10,
    },
    'step': {
        'x': 2,
        'y': 2,
        'z': 2,
    },
    'acquisition': {
        'settling_time': 0.5,  # seconds
        'sample_rate': 1e6,    # S/s
        'num_samples': 10000,
        'voltage_range': 0.1,  # V
    },
    'options': {
        'home_before': False,
        'home_after': False,
        'output': 'scan_result',
    },
}


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Merge with defaults for any missing values
    merged = DEFAULT_CONFIG.copy()
    for section, values in config.items():
        if section in merged and isinstance(merged[section], dict):
            merged[section] = {**merged[section], **values}
        else:
            merged[section] = values

    return merged


def progress_callback(current: int, total: int, point):
    """Print scan progress."""
    pct = 100 * current / total
    print(
        f"\r[{current}/{total}] ({pct:.1f}%) "
        f"({point.x:.1f}, {point.y:.1f}, {point.z:.1f}) "
        f"intensity={point.intensity:.6f}V",
        end='',
        flush=True,
    )
    if current == total:
        print()  # Newline at end


def cmd_scan(args):
    """Execute a 3D scan."""
    config = load_config(args.config)

    dev = config['device']
    pos = config['position']
    rng = config['range']
    step = config['step']
    acq = config['acquisition']
    opts = config['options']

    params = ScanParameters(
        start_x=pos['x'],
        start_y=pos['y'],
        start_z=pos['z'],
        x_range=(-rng['x'], rng['x']),
        y_range=(-rng['y'], rng['y']),
        z_range=(-rng['z'], rng['z']),
        step_x=step['x'],
        step_y=step['y'],
        step_z=step['z'],
        settling_time=acq['settling_time'],
        sample_rate=acq['sample_rate'],
        num_samples=acq['num_samples'],
        voltage_range=acq['voltage_range'],
    )

    print(f"Config: {args.config}")
    print(f"Scan parameters:")
    print(f"  Center: ({pos['x']}, {pos['y']}, {pos['z']}) mm")
    print(f"  Range: X±{rng['x']}, Y±{rng['y']}, Z±{rng['z']} mm")
    print(f"  Step: ({step['x']}, {step['y']}, {step['z']}) mm")
    print(f"  Total points: {params.total_points()}")
    print(f"  Settling time: {acq['settling_time']}s")
    print(f"  Sample rate: {acq['sample_rate']/1e6:.1f} MS/s, {acq['num_samples']} samples")
    print()

    scanner = Scanner(
        printer_port=dev['printer_port'],
        printer_baudrate=dev['printer_baud'],
        hydrophone_channel=dev['hydrophone_channel'],
    )

    try:
        print("Connecting to devices...")
        scanner.connect()
        print("Connected.")

        if opts['home_before']:
            print("Homing printer...")
            scanner.home()

        print("Starting scan...")
        result = scanner.scan(
            params,
            progress_callback=progress_callback,
            home_before=False,  # Already homed if requested
            home_after=opts['home_after'],
        )

        print(f"\nScan complete. {len(result.points)} points acquired.")

        output = opts['output']
        if output:
            result.save(output)
            print(f"Results saved to {output}.json and {output}.npz")

    except KeyboardInterrupt:
        print("\n\nScan aborted by user.")
        scanner.abort()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        scanner.disconnect()


def cmd_view(args):
    """View scan results."""
    import matplotlib.pyplot as plt

    print(f"Loading {args.file}...")
    result = ScanResult.load(args.file)
    print(f"Loaded {len(result.points)} points.")

    interpolation = 'bicubic' if args.interpolate else 'nearest'

    if args.scatter:
        print("Generating 3D scatter plot...")
        plot_3d_scatter(result, cmap=args.cmap)

    if args.slice:
        plane, pos = args.slice.split(':') if ':' in args.slice else (args.slice, None)
        pos = float(pos) if pos else None
        print(f"Generating {plane.upper()} slice{' (interpolated)' if args.interpolate else ''}...")
        plot_slice(result, plane=plane, position=pos, cmap=args.cmap, interpolation=interpolation)

    if args.interactive:
        plane = args.interactive
        print(f"Opening interactive {plane.upper()} slice viewer{' (interpolated)' if args.interpolate else ''}...")
        interactive_slice_viewer(result, plane=plane, cmap=args.cmap, interpolation=interpolation)

    if args.all_slices:
        plane = args.all_slices
        print(f"Generating all {plane.upper()} slices{' (interpolated)' if args.interpolate else ''}...")
        plot_all_slices(result, plane=plane, cmap=args.cmap, interpolation=interpolation)

    # Default: show 3D scatter if no visualization specified
    if not any([args.scatter, args.slice, args.interactive, args.all_slices]):
        print("Generating 3D scatter plot (default)...")
        plot_3d_scatter(result, cmap=args.cmap)

    plt.show()


def cmd_info(args):
    """Show info about scan file."""
    result = ScanResult.load(args.file)
    p = result.parameters

    print(f"Scan file: {args.file}")
    print(f"Points: {len(result.points)}")
    print()
    print("Parameters:")
    print(f"  Center: ({p.start_x}, {p.start_y}, {p.start_z}) mm")
    print(f"  X range: [{p.x_range[0]}, {p.x_range[1]}] mm (step: {p.step_x})")
    print(f"  Y range: [{p.y_range[0]}, {p.y_range[1]}] mm (step: {p.step_y})")
    print(f"  Z range: [{p.z_range[0]}, {p.z_range[1]}] mm (step: {p.step_z})")
    print(f"  Settling time: {p.settling_time}s")
    print(f"  Sample rate: {p.sample_rate/1e6:.1f} MS/s")
    print(f"  Samples: {p.num_samples}")
    print(f"  Voltage range: {p.voltage_range}V")

    if result.points:
        intensities = [pt.intensity for pt in result.points]
        print()
        print("Intensity statistics:")
        print(f"  Min: {min(intensities):.6f}V")
        print(f"  Max: {max(intensities):.6f}V")
        print(f"  Mean: {sum(intensities)/len(intensities):.6f}V")


def cmd_init(args):
    """Generate a sample config file."""
    output = args.output or 'scan_config.yaml'

    # Add comments to the YAML output
    config_with_comments = f"""\
# Papillion Scan Configuration

device:
  printer_port: /dev/ttyUSB0
  printer_baud: 115200
  hydrophone_channel: 0

# Center position of scan (mm)
position:
  x: 0
  y: 0
  z: 100

# Range around center position (±mm)
range:
  x: 10
  y: 10
  z: 10

# Step size for each axis (mm)
step:
  x: 2
  y: 2
  z: 2

# Acquisition settings
acquisition:
  settling_time: 0.5    # seconds to wait after move
  sample_rate: 1000000  # samples per second
  num_samples: 10000    # samples per acquisition
  voltage_range: 0.1    # input voltage range (V)

# Scan options
options:
  home_before: false
  home_after: false
  output: scan_result   # output file base name
"""

    with open(output, 'w') as f:
        f.write(config_with_comments)

    print(f"Created config file: {output}")


def main():
    parser = argparse.ArgumentParser(
        description='Papillion - 3D Hydrophone Scanning System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Generate sample config file')
    init_parser.add_argument('-o', '--output', help='Output file (default: scan_config.yaml)')
    init_parser.set_defaults(func=cmd_init)

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Execute a 3D scan')
    scan_parser.add_argument('config', help='YAML config file')
    scan_parser.set_defaults(func=cmd_scan)

    # View command
    view_parser = subparsers.add_parser('view', help='Visualize scan results')
    view_parser.add_argument('file', help='Scan file (without extension)')
    view_parser.add_argument('--scatter', action='store_true', help='Show 3D scatter plot')
    view_parser.add_argument('--slice', help='Show slice (xy, xz, yz or xy:50 for position)')
    view_parser.add_argument('--interactive', metavar='PLANE', help='Interactive slice viewer (xy, xz, yz)')
    view_parser.add_argument('--all-slices', metavar='PLANE', help='Show all slices (xy, xz, yz)')
    view_parser.add_argument('--cmap', default='viridis', help='Colormap (default: viridis)')
    view_parser.add_argument('--interpolate', action='store_true', help='Show interpolated field (bicubic) instead of raw data')
    view_parser.set_defaults(func=cmd_view)

    # Info command
    info_parser = subparsers.add_parser('info', help='Show scan file info')
    info_parser.add_argument('file', help='Scan file (without extension)')
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
