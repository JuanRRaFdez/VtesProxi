import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from desktop.runtime import default_portable_dir, default_seed_dir, ensure_seeded_runtime


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Launch WebVTES locally on Windows.')
    parser.add_argument('--serve', action='store_true', help='Run the local Django server')
    parser.add_argument('--port', type=int, default=8000, help='Preferred local port')
    parser.add_argument('--portable-dir', default='', help='Portable runtime directory')
    parser.add_argument('--seed-dir', default='', help='Seed directory for first run')
    return parser.parse_args(argv)


def _ensure_project_root_on_path():
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    return project_root


def choose_port(preferred_port=8000, attempts=20):
    for port in range(preferred_port, preferred_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', port))
            except OSError:
                continue
            return port
    raise RuntimeError('No free local port found')


def build_server_command(port, portable_dir, seed_dir):
    base_command = [sys.executable]
    if getattr(sys, 'frozen', False):
        return base_command + [
            '--serve',
            '--port',
            str(port),
            '--portable-dir',
            str(portable_dir),
            '--seed-dir',
            str(seed_dir),
        ]

    return base_command + [
        str(Path(__file__).resolve()),
        '--serve',
        '--port',
        str(port),
        '--portable-dir',
        str(portable_dir),
        '--seed-dir',
        str(seed_dir),
    ]


def wait_for_server(port, timeout_seconds=30):
    deadline = time.time() + timeout_seconds
    url = f'http://127.0.0.1:{port}/login/'
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def run_server(port, portable_dir):
    _ensure_project_root_on_path()
    os.environ['DJANGO_SETTINGS_MODULE'] = 'webvtes.settings_desktop'
    os.environ['WEBVTES_PORTABLE_DIR'] = str(portable_dir)

    from django.core.management import execute_from_command_line

    execute_from_command_line([
        'manage.py',
        'runserver',
        f'127.0.0.1:{port}',
        '--noreload',
    ])


def run_supervisor(port, portable_dir, seed_dir):
    ensure_seeded_runtime(portable_dir, seed_dir)
    resolved_port = choose_port(port)
    command = build_server_command(resolved_port, portable_dir, seed_dir)
    subprocess.Popen(command, cwd=str(Path(__file__).resolve().parent.parent))

    if not wait_for_server(resolved_port):
        raise RuntimeError(f'Local server did not start on port {resolved_port}')

    webbrowser.open(f'http://127.0.0.1:{resolved_port}/login/')
    return resolved_port


def main(argv=None):
    args = parse_args(argv)
    portable_dir = Path(args.portable_dir) if args.portable_dir else default_portable_dir()
    seed_dir = Path(args.seed_dir) if args.seed_dir else default_seed_dir()

    if args.serve:
        run_server(args.port, portable_dir)
        return 0

    run_supervisor(args.port, portable_dir, seed_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
