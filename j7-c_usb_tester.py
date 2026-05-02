#!/usr/bin/env python3
import serial
import datetime
import contextlib
import binascii
import struct
import sys
import argparse
import csv
import time
import socket
import re

def is_mac_address(port):
    return re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', port)

def parse_data(data_pkt):
    if not data_pkt or len(data_pkt) != 36:
        return None
    if not data_pkt.startswith(b'\xFF\x55'):
        return None

    def _get_duration(pkt):
        return datetime.timedelta(days=pkt[0], hours=pkt[1], minutes=pkt[2], seconds=pkt[3])

    return {
            'voltage': struct.unpack('>I', (b'\x00' + data_pkt[4:7]))[0]/100,
            'current': struct.unpack('>I', (b'\x00' + data_pkt[7:10]))[0]/100,
            'mAh': struct.unpack('>I', (b'\x00' + data_pkt[10:13]))[0],
            'Wh': struct.unpack('>I', data_pkt[13:17])[0]/100,
            'D+': struct.unpack('>H', data_pkt[17:19])[0]/100,
            'D-': struct.unpack('>H', data_pkt[19:21])[0]/100,
            'temperature': struct.unpack('>H', data_pkt[21:23])[0],
            'duration': _get_duration(data_pkt[23:27]),
        }


def read_data(port, relative_values=False):
    is_bt = is_mac_address(port)
    s = None
    initial_reading = None
    while True:
        try:
            if is_bt:
                s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                s.connect((port, 1))
            else:
                s = serial.Serial(port, timeout=3)
            while True:
                if is_bt:
                    data = s.recv(36)
                else:
                    data = s.read(36)
                if data:
                    parsed = parse_data(data)
                    if parsed:
                        if relative_values:
                            if initial_reading is None:
                                initial_reading = parsed
                            else:
                                for key in ('mAh', 'Wh', 'duration'):
                                    parsed[key] -= initial_reading[key]
                        yield (data, parsed)
        except (serial.serialutil.SerialException, OSError) as ex:
            print("\nException: {ex}\n")
            time.sleep(3)
        except KeyboardInterrupt:
            break
        finally:
            if s:
                s.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', help='csv output filename')
    parser.add_argument('--relative_values', action='store_true', help='Energy values are relative to the first reading')
    parser.add_argument('--debug', action='store_true', help='Print debug information')
    parser.add_argument('device_port', help='Linux bluetooth rfcomm device path, Windows COM port, or Bluetooth MAC address')
    return parser.parse_args()


def format_values(key, value):
    if key in ('voltage', 'current', 'mAh', 'Wh'):
        return f"{value:.2f}"
    elif key in ('D+', 'D-'):
        return f"{value:.1f}"
    else:
        return str(value)

def main():
    args = parse_args()
    if args.device_port:
        csv_file = None
        csv_writer = None
        try:
            for data, parsed_data in read_data(args.device_port, relative_values=args.relative_values):
                if not csv_writer and args.csv:
                    csv_file = open(args.csv, 'w', newline='')
                    csv_writer = csv.DictWriter(csv_file, fieldnames=parsed_data.keys())
                    csv_writer.writeheader()
 
                if csv_writer:
                    csv_writer.writerow(parsed_data)

                if args.debug:
                    print(binascii.hexlify(data).decode('utf-8'), parsed_data)
                else:
                    # Print a nice in-place update key-value pairs
                    print(f"        \r{', '.join(f'{k}: {format_values(k, v)}' for k, v in parsed_data.items())} ", end='', flush=True)

        except KeyboardInterrupt:
            pass
        finally:
            if csv_file:
                csv_file.close()


if __name__ == '__main__':
    main()
