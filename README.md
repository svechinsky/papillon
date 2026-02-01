# Papillion - 3D Hydrophone Scanning System

Papillion is an automated 3D acoustic field measurement system that coordinates a FLSUN 3D printer (used as a 3-axis positioning system) with Digilent Analog Discovery hardware for hydrophone-based acoustic measurements. It creates detailed 3D maps of acoustic intensity in water.

## Features

- **3D Raster Scanning** - Automated scanning with configurable grid resolution and range
- **Bidirectional Scanning** - Optimized path planning minimizes travel time
- **Real-time Feedback** - Progress display during scans with position and intensity
- **Multiple Visualization Options** - 3D scatter plots, 2D slices, interactive viewers
- **Data Persistence** - Results saved as JSON metadata + NumPy arrays
- **Configurable Acquisition** - Adjustable sample rate, buffer size, and voltage range

## Requirements

### Hardware

- **FLSUN 3D Printer** - Any FLSUN printer with G-code support (used as positioning system)
- **Digilent Analog Discovery** - For oscilloscope-based hydrophone signal acquisition
- **Hydrophone** - Connected to Analog Discovery analog input
- **Transducer** - should run separetly ideally in contious mode

### Software

- Python 3.11 or higher
- [Digilent WaveForms Runtime](https://digilent.com/shop/software/digilent-waveforms/) - Required for Analog Discovery hardware
ge
- Can download directly with
` wget "https://files.digilent.com/Software/Adept2%20Runtime/2.27.9/digilent.adept.runtime_2.27.9-amd64.deb"`
And
`wget https://files.digilent.com/Software/Waveforms/3.24.3/digilent.waveforms_3.24.3_amd64.deb`
 
### Digilent WaveForms Installation (Ubuntu/Debian)

Install the Digilent runtime and WaveForms software:

```bash
# Install runtime (included in repo)
sudo dpkg -i digilent.adept.runtime_2.27.9-amd64.deb

# Install WaveForms
sudo dpkg -i digilent.waveforms_3.24.3_amd64.deb

# Fix any missing dependencies
sudo apt-get install -f
```

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd papillion

# Install dependencies
uv sync
```

## Configuration

Create a configuration file or generate a sample one:

```bash
python main.py init -o my_config.yaml
```

### Configuration File Structure

```yaml
device:
  printer_port: /dev/ttyUSB0      # Serial port for FLSUN printer
  printer_baud: 115200            # Baud rate (default: 115200)
  hydrophone_channel: 0           # Analog input channel (0 or 1)

position:                         # Center position of scan (mm)
  x: -2
  y: -82
  z: 146.5

range:                            # Scan range around center (±mm)
  x: 3
  y: 3
  z: 6

step:                             # Step size for each axis (mm)
  x: 2
  y: 2
  z: 3

acquisition:
  settling_time: 0.5              # Delay after movement (seconds)
  sample_rate: 1000000            # Samples per second (1 MS/s)
  num_samples: 1000000            # Samples per acquisition
  voltage_range: 0.1              # Input range in volts

hydrophone:
  sensitivity_db: -250            # Calibration: dB re 1V/µPa
  frequency_khz: 250              # Operating frequency (kHz)

options:
  home_before: false              # Home printer before scan
  home_after: false               # Home printer after scan
  output: scan_result             # Output file base name
```

## Usage

### Running a Scan

```bash
python main.py scan scan_config.yaml
```

This will:
1. Connect to the printer and hydrophone
2. Perform a 3D raster scan across the defined grid
3. Display real-time progress with position and intensity
4. Save results to `{output}.json` and `{output}.npz`

### Viewing Results

**3D Scatter Plot (default):**
```bash
python main.py view scan_result
```

**2D Slice at specific coordinate:**
```bash
# XY plane at Z=146.5mm
python main.py view scan_result --slice xy:146.5

# XZ plane at Y=-82mm
python main.py view scan_result --slice xz:-82

# YZ plane at X=-2mm
python main.py view scan_result --slice yz:-2
```

**Interactive Slice Viewer:**
```bash
# Navigate through Z slices with a slider
python main.py view scan_result --interactive xy

# Navigate through Y slices
python main.py view scan_result --interactive xz
```

**All Slices in Grid:**
```bash
python main.py view scan_result --all-slices xy
```

**Additional Options:**
```bash
# With interpolation for smoother visualization
python main.py view scan_result --slice xy --interpolate

# Custom colormap
python main.py view scan_result --slice xy --cmap hot

# Combined options
python main.py view scan_result --slice xy:146.5 --interpolate --cmap viridis
```

### Viewing Scan Metadata

```bash
python main.py info scan_result
```

Displays scan parameters, point count, and intensity statistics.

### Standalone Printer Control

The printer can be controlled independently for setup and testing:

```bash
# List available serial ports
python flsun_control.py -l

# Home the printer
python flsun_control.py -p /dev/ttyUSB0 -c "G28"

# Move to position
python flsun_control.py -p /dev/ttyUSB0 -c "G0 X0 Y-80 Z150"

# Interactive mode
python flsun_control.py -p /dev/ttyUSB0
```

**Interactive Mode Commands:**
- Enter G-code commands directly (e.g., `G28`, `G0 X10 Y20 Z30`)
- `status` - Show printer position and temperature
- `quit` or `exit` - Exit interactive mode

## Project Structure

```
papillion/
├── main.py              # CLI entry point
├── scanner.py           # Scan orchestration
├── flsun_control.py     # FLSUN printer G-code interface
├── hydrophone.py        # Digilent Analog Discovery interface
├── scan_data.py         # Data structures (ScanParameters, ScanPoint, ScanResult)
├── visualization.py     # Plotting and visualization functions
├── scan_config.yaml     # Example configuration file
├── pyproject.toml       # Project dependencies
└── README.md            # This file
```

## Output Files

After a scan completes, two files are created:

- **`{output}.json`** - Metadata including scan parameters and point data
- **`{output}.npz`** - NumPy arrays for efficient data loading:
  - `x`, `y`, `z` - Position coordinates
  - `intensity` - Peak-to-peak amplitude (primary metric)
  - `rms` - RMS amplitude
  - `peak_amplitude` - Peak amplitude

## Scanning Workflow

1. **Configuration** - Define scan grid, acquisition parameters, and device settings
2. **Connection** - System connects to printer (serial) and hydrophone (Digilent)
3. **Grid Generation** - Bidirectional raster path is computed
4. **Scanning** - For each grid point:
   - Move printer to position
   - Wait for settling time
   - Acquire hydrophone signal
   - Compute intensity metrics
5. **Save Results** - Write JSON and NPZ files
6. **Visualization** - View results using built-in plotting tools

## Troubleshooting

### Printer Connection Issues

- Ensure the correct serial port is specified (use `python flsun_control.py -l` to list ports)
- Check that the printer is powered on and connected via USB
- Verify the user has permission to access the serial port:
  ```bash
  sudo usermod -a -G dialout $USER
  # Log out and back in for changes to take effect
  ```

### Digilent Device Not Found

- Ensure WaveForms runtime is installed
- Check that the Analog Discovery is connected via USB
- Try running WaveForms application to verify device detection

### No Data in Scan Results

- Verify hydrophone is connected to the correct channel
- Check voltage range is appropriate for signal amplitude
- Ensure sample rate is sufficient for signal frequency

