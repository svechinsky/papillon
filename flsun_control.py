#!/usr/bin/env python3
"""
FLSUN Printer Control Script
Control an FLSUN 3D printer via serial port using G-code commands.
"""

import serial
import serial.tools.list_ports
import sys
import time
import argparse
import readline  # Enables command history with arrow keys


class FLSunPrinter:
    def __init__(self, port, baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect(self):
        """Connect to the printer."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for printer to initialize
            self._flush_startup()
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False

    def _flush_startup(self):
        """Read and discard startup messages."""
        while self.serial.in_waiting:
            self.serial.readline()

    def disconnect(self):
        """Disconnect from the printer."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected")

    def send_command(self, command, wait_for_ok=True):
        """Send a G-code command and return the response."""
        if not self.serial or not self.serial.is_open:
            print("Not connected to printer")
            return None

        command = command.strip()
        if not command:
            return None

        # Send command
        self.serial.write(f"{command}\n".encode())

        responses = []
        while True:
            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                if not wait_for_ok:
                    break
                continue
            responses.append(line)
            if line.startswith('ok') or line.startswith('error'):
                break

        return responses

    def home(self, axis=None):
        """Home the printer. Optionally specify axis (X, Y, Z)."""
        if axis:
            return self.send_command(f"G28 {axis.upper()}")
        return self.send_command("G28")

    def move(self, x=None, y=None, z=None, feedrate=3000):
        """Move to absolute position."""
        cmd = "G0"
        if x is not None:
            cmd += f" X{x}"
        if y is not None:
            cmd += f" Y{y}"
        if z is not None:
            cmd += f" Z{z}"
        cmd += f" F{feedrate}"
        return self.send_command(cmd)

    def move_relative(self, x=None, y=None, z=None, feedrate=3000):
        """Move relative to current position."""
        self.send_command("G91")  # Relative positioning
        result = self.move(x, y, z, feedrate)
        self.send_command("G90")  # Back to absolute
        return result

    def set_temperature(self, temp, wait=False):
        """Set hotend temperature."""
        cmd = "M109" if wait else "M104"
        return self.send_command(f"{cmd} S{temp}")

    def set_bed_temperature(self, temp, wait=False):
        """Set bed temperature."""
        cmd = "M190" if wait else "M140"
        return self.send_command(f"{cmd} S{temp}")

    def get_temperature(self):
        """Get current temperatures."""
        return self.send_command("M105")

    def get_position(self):
        """Get current position."""
        return self.send_command("M114")

    def motors_off(self):
        """Disable all stepper motors."""
        return self.send_command("M84")

    def fan_on(self, speed=255):
        """Turn on part cooling fan (0-255)."""
        return self.send_command(f"M106 S{speed}")

    def fan_off(self):
        """Turn off part cooling fan."""
        return self.send_command("M107")

    def emergency_stop(self):
        """Emergency stop."""
        return self.send_command("M112", wait_for_ok=False)

    def get_firmware_info(self):
        """Get firmware information."""
        return self.send_command("M115")


def list_ports():
    """List available serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found")
        return
    print("Available serial ports:")
    for port in ports:
        print(f"  {port.device} - {port.description}")


def interactive_mode(printer):
    """Run interactive command mode."""
    print("\nInteractive mode. Type 'help' for commands, 'quit' to exit.")

    shortcuts = {
        'home': ('G28', 'Home all axes'),
        'homex': ('G28 X', 'Home X axis'),
        'homey': ('G28 Y', 'Home Y axis'),
        'homez': ('G28 Z', 'Home Z axis'),
        'pos': ('M114', 'Get current position'),
        'temp': ('M105', 'Get temperatures'),
        'info': ('M115', 'Get firmware info'),
        'off': ('M84', 'Motors off'),
        'fanon': ('M106 S255', 'Fan on full'),
        'fanoff': ('M107', 'Fan off'),
        'stop': ('M112', 'Emergency stop'),
        'cooldown': ('M104 S0\nM140 S0', 'Turn off heaters'),
    }

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        if cmd.lower() == 'quit' or cmd.lower() == 'exit':
            break
        elif cmd.lower() == 'help':
            print("\nShortcut commands:")
            for name, (gcode, desc) in shortcuts.items():
                print(f"  {name:10} - {desc} ({gcode})")
            print("\n  Or enter any G-code command directly (e.g., G0 X100 Y100)")
            print("  quit/exit - Exit the program")
        elif cmd.lower() in shortcuts:
            gcode, desc = shortcuts[cmd.lower()]
            print(f"Sending: {gcode}")
            for line in gcode.split('\n'):
                responses = printer.send_command(line)
                if responses:
                    for r in responses:
                        print(f"  {r}")
        else:
            responses = printer.send_command(cmd)
            if responses:
                for r in responses:
                    print(f"  {r}")


def main():
    parser = argparse.ArgumentParser(description='FLSUN Printer Control')
    parser.add_argument('-p', '--port', help='Serial port (e.g., /dev/ttyUSB0)')
    parser.add_argument('-b', '--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('-l', '--list', action='store_true', help='List available serial ports')
    parser.add_argument('-c', '--command', help='Send a single G-code command and exit')

    args = parser.parse_args()

    if args.list:
        list_ports()
        return

    if not args.port:
        print("Error: Serial port required. Use -l to list available ports.")
        print("Example: python flsun_control.py -p /dev/ttyUSB0")
        sys.exit(1)

    printer = FLSunPrinter(args.port, args.baud)

    if not printer.connect():
        sys.exit(1)

    try:
        if args.command:
            responses = printer.send_command(args.command)
            if responses:
                for r in responses:
                    print(r)
        else:
            interactive_mode(printer)
    finally:
        printer.disconnect()


if __name__ == '__main__':
    main()
