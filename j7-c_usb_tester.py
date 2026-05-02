#!/usr/bin/env python3
import serial
import datetime
import binascii
import struct
import sys
import argparse
import csv
import time
import socket
import re
import threading
import json
import os
from collections import deque

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

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
                        else:
                            yield (data, parsed)
        except (serial.serialutil.SerialException, OSError) as ex:
            print("\nException: {}\n".format(str(ex)))
            time.sleep(3)
        except KeyboardInterrupt:
            break
        finally:
            if s:
                s.close()


# --- Web dashboard ---

_web_readings = deque()
_web_base = 0
_web_lock = threading.Lock()
_MAX_WEB_READINGS = 10000


def _add_web_reading(parsed):
    global _web_base
    r = {
        'voltage':     parsed['voltage'],
        'current':     parsed['current'],
        'mAh':         parsed['mAh'],
        'Wh':          parsed['Wh'],
        'D+':          parsed['D+'],
        'D-':          parsed['D-'],
        'temperature': parsed['temperature'],
        'duration':    parsed['duration'].total_seconds(),
        'power':       round(parsed['voltage'] * parsed['current'], 2),
    }
    with _web_lock:
        _web_readings.append(r)
        if len(_web_readings) > _MAX_WEB_READINGS:
            _web_readings.popleft()
            _web_base += 1


def _get_web_readings(client_from_idx=0):
    with _web_lock:
        total = _web_base + len(_web_readings)
        local_from = max(0, client_from_idx - _web_base)
        return list(_web_readings)[local_from:], total


def start_web_server(port):
    try:
        import bottle
        from bottle import Bottle, request as bottle_request, response as bottle_response, static_file, template
    except ImportError:
        print("Error: 'bottle' package is required for --web. Install with: pip install bottle")
        sys.exit(1)

    from wsgiref.simple_server import make_server, WSGIServer
    from socketserver import ThreadingMixIn

    class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    bottle.TEMPLATE_PATH.insert(0, os.path.join(_SCRIPT_DIR, 'views'))
    _static_root = os.path.join(_SCRIPT_DIR, 'static')

    app = Bottle()

    @app.route('/')
    def index():
        _, total = _get_web_readings()
        return template('dashboard', initial_idx=total)

    @app.route('/static/<filepath:path>')
    def serve_static(filepath):
        return static_file(filepath, root=_static_root)

    @app.route('/api/data')
    def api_data():
        bottle_response.content_type = 'application/json'
        bottle_response.set_header('Cache-Control', 'no-cache')
        from_idx = int(bottle_request.query.get('from', 0))
        data, total = _get_web_readings(from_idx)
        return json.dumps({'readings': data, 'total': total})

    httpd = make_server('0.0.0.0', port, app, server_class=_ThreadingWSGIServer)
    httpd.serve_forever()


# --- CLI ---

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', help='csv output filename')
    parser.add_argument('--relative_values', action='store_true', help='Energy values are relative to the first reading')
    parser.add_argument('--debug', action='store_true', help='Print debug information')
    parser.add_argument('--web', nargs='?', const=8080, type=int, metavar='PORT',
                        help='Start web dashboard on PORT (default: 8080)')
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
        if args.web is not None:
            t = threading.Thread(target=start_web_server, args=(args.web,), daemon=True)
            t.start()
            print(f"Web dashboard: http://localhost:{args.web}/")

        csv_file = None
        csv_writer = None
        try:
            for data, parsed_data in read_data(args.device_port, relative_values=args.relative_values):
                if args.web is not None:
                    _add_web_reading(parsed_data)

                if not csv_writer and args.csv:
                    csv_file = open(args.csv, 'w', newline='')
                    csv_writer = csv.DictWriter(csv_file, fieldnames=parsed_data.keys())
                    csv_writer.writeheader()

                if csv_writer:
                    csv_writer.writerow(parsed_data)

                if args.debug:
                    print(binascii.hexlify(data).decode('utf-8'), parsed_data)
                elif not args.web:
                    # Print a nice in-place update key-value pairs
                    print(f"        \r{', '.join(f'{k}: {format_values(k, v)}' for k, v in parsed_data.items())} ", end='', flush=True)

        except KeyboardInterrupt:
            pass
        finally:
            if csv_file:
                csv_file.close()


if __name__ == '__main__':
    main()
