"""
Folder watcher for SECOM daily analysis.

Watches the ./input/ folder. When a new CSV file is created,
waits for the file to be fully written, then runs run_analyze.bat.

Usage:
    > conda activate <your_env>
    > python watch_folder.py

Press Ctrl+C to stop.
"""

import os
import sys
import time
import subprocess
import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# ===== Paths =====
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / 'input'
BAT_FILE = SCRIPT_DIR / 'run_analyze.bat'

# ===== Settings =====
# Wait time before processing (seconds). Lets the file finish writing.
STABILIZE_WAIT = 2.0
# Max wait for file size to stabilize (seconds).
MAX_STABILIZE_TRIES = 10


def log(message):
    """Print a message with timestamp."""
    now = datetime.datetime.now().strftime('%H:%M:%S')
    print(f'[{now}] {message}', flush=True)


def wait_until_stable(file_path):
    """Wait until the file size stops changing.

    Large files take time to copy. We must wait until the copy is done
    before reading the file.
    """
    last_size = -1
    for _ in range(MAX_STABILIZE_TRIES):
        try:
            current_size = file_path.stat().st_size
        except OSError:
            time.sleep(STABILIZE_WAIT)
            continue
        if current_size == last_size and current_size > 0:
            return True
        last_size = current_size
        time.sleep(STABILIZE_WAIT)
    return False


def run_analysis():
    """Run the analyze batch file."""
    if not BAT_FILE.exists():
        log(f'ERROR: {BAT_FILE.name} not found.')
        return
    log(f'Running {BAT_FILE.name}...')
    try:
        result = subprocess.run(
            [str(BAT_FILE)],
            cwd=str(SCRIPT_DIR),
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            log('Analysis finished OK.')
        else:
            log(f'Analysis exited with code {result.returncode}.')
            if result.stderr:
                log(f'  stderr: {result.stderr[:200]}')
    except subprocess.TimeoutExpired:
        log('ERROR: analysis timed out after 5 minutes.')
    except Exception as e:
        log(f'ERROR running analysis: {e}')


class NewFileHandler(FileSystemEventHandler):
    """Reacts to new files in the watched folder."""

    def __init__(self):
        super().__init__()
        # Track files we already handled, to skip duplicate events.
        self.handled = set()

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        # Only react to CSV files starting with "secom_"
        if not file_path.name.startswith('secom_'):
            return
        if not file_path.name.endswith('.csv'):
            return
        # Skip if already handled in this session
        if file_path.name in self.handled:
            return

        log(f'New file detected: {file_path.name}')
        log('  Waiting for file to finish writing...')
        if not wait_until_stable(file_path):
            log('  WARNING: file size did not stabilize. Trying anyway.')
        else:
            log('  File is stable.')

        self.handled.add(file_path.name)
        run_analysis()


def main():
    INPUT_DIR.mkdir(exist_ok=True)
    log(f'Watching folder: {INPUT_DIR}')
    log(f'Trigger: any new secom_*.csv file')
    log(f'Will run: {BAT_FILE.name}')
    log('Press Ctrl+C to stop.')
    print('-' * 50, flush=True)

    handler = NewFileHandler()
    observer = Observer()
    observer.schedule(handler, str(INPUT_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log('Stop signal received.')
        observer.stop()
    observer.join()
    log('Watcher stopped.')


if __name__ == '__main__':
    main()
