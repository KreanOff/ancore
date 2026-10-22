#!/usr/bin/env python3
"""Compatibility entry point; configuration and service operations live in deploy/."""
import argparse
import os
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--env-file', type=Path, default=root / 'deploy/.env')
    parser.add_argument('--context')
    parser.add_argument('command', choices=('configure', 'install', 'update', 'backup',
                                          'status', 'stop', 'start', 'unlock', 'reload',
                                          'admin', 'restore'))
    args, remaining = parser.parse_known_args()
    configuration = str(args.env_file.resolve())
    if args.command == 'configure':
        os.execv(sys.executable, [sys.executable, str(root / 'deploy/cli/configure.py'),
                                 '--env-file', configuration, *remaining])
    command = ['sh', str(root / 'ancore.sh'), '--env-file', configuration]
    if args.context:
        command += ['--context', args.context]
    os.execv('/bin/sh', [*command, args.command, *remaining])


if __name__ == '__main__':
    main()
