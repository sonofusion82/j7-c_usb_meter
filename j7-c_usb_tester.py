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
import os
import threading
import json
from bottle import route, run, response, static_file, template, TEMPLATE_PATH

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


def read_data(port, relative_values=False, stop_event=None):
    is_bt = is_mac_address(port)
    s = None
    initial_reading = None
    while not (stop_event and stop_event.is_set()):
        try:
            if is_bt:
                s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                s.connect((port, 1))
            else:
                s = serial.Serial(port, timeout=3)
            while not (stop_event and stop_event.is_set()):
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
                        else:
                            yield (data, parsed)
        except (serial.serialutil.SerialException, OSError) as ex:
            print(f"\nException: {ex}\n")
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
    parser.add_argument('--web', action='store_true', help='Start web server with live dashboard')
    parser.add_argument('--port', type=int, default=8080, help='Web server port (default: 8080)')
    parser.add_argument('device_port', help='Linux bluetooth rfcomm device path, Windows COM port, or Bluetooth MAC address')
    return parser.parse_args()


def format_values(key, value):
    if key in ('voltage', 'current', 'mAh', 'Wh'):
        return f"{value:.2f}"
    elif key in ('D+', 'D-'):
        return f"{value:.1f}"
    else:
        return str(value)


_MAX_WEB_HISTORY = 3600
_web_measurements = []
_web_measurements_lock = threading.Lock()
_web_stop_event = threading.Event()

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH.insert(0, os.path.join(_SCRIPT_DIR, 'views'))
_STATIC_ROOT = os.path.join(_SCRIPT_DIR, 'static')


@route('/static/<filepath:path>')
def _serve_static(filepath):
    return static_file(filepath, root=_STATIC_ROOT)


@route('/')
def _serve_dashboard():
    response.content_type = 'text/html; charset=utf-8'
    return template('dashboard')


@route('/api/data')
def _serve_data():
    response.content_type = 'application/json'
    with _web_measurements_lock:
        return {'data': list(_web_measurements)}


def main():
    args = parse_args()
    if args.web:
        _web_stop_event.clear()
        collector = threading.Thread(
            target=_web_data_collector,
            args=(args.device_port, args.csv, args.relative_values),
            daemon=True,
        )
        collector.start()
        print(f"Dashboard: http://localhost:{args.port}")
        try:
            run(host='0.0.0.0', port=args.port, quiet=True)
        except KeyboardInterrupt:
            pass
        finally:
            _web_stop_event.set()
        return

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
                    print(f"        \r{', '.join(f'{k}: {format_values(k, v)}' for k, v in parsed_data.items())} ", end='', flush=True)

        except KeyboardInterrupt:
            pass
        finally:
            if csv_file:
                csv_file.close()


def _web_data_collector(port, csv_filename, relative_values):
    csv_file = None
    csv_writer = None
    try:
        for data, parsed_data in read_data(port, relative_values=relative_values, stop_event=_web_stop_event):
            if not csv_writer and csv_filename:
                csv_file = open(csv_filename, 'w', newline='')
                csv_writer = csv.DictWriter(csv_file, fieldnames=parsed_data.keys())
                csv_writer.writeheader()

            if csv_writer:
                csv_writer.writerow(parsed_data)

            entry = {
                'voltage': parsed_data['voltage'],
                'current': parsed_data['current'],
                'mAh': parsed_data['mAh'],
                'Wh': parsed_data['Wh'],
                'D+': parsed_data['D+'],
                'D-': parsed_data['D-'],
                'temperature': parsed_data['temperature'],
                'duration': str(parsed_data['duration']),
                'timestamp': datetime.datetime.now().isoformat(),
            }
            with _web_measurements_lock:
                _web_measurements.append(entry)
                if len(_web_measurements) > _MAX_WEB_HISTORY:
                    _web_measurements[:] = _web_measurements[-_MAX_WEB_HISTORY:]
    finally:
        if csv_file:
            csv_file.close()


if __name__ == '__main__':
    main()
