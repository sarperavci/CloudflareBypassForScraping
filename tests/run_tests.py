#!/usr/bin/env python3
import subprocess
import sys
import time
import signal
import urllib.request
import urllib.error
from pathlib import Path

SERVER_READY_TIMEOUT = 30  # seconds to wait for /cache/stats


def print_banner(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def wait_for_server(process, url="http://localhost:8000/cache/stats", timeout=SERVER_READY_TIMEOUT):
    """Poll /cache/stats until the server answers; False if it dies or times out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.25)
    return False


def start_server():
    print("Starting server...")
    process = subprocess.Popen(
        [sys.executable, "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent
    )

    print("Waiting for server to initialize...")
    if not wait_for_server(process):
        print("Server failed to start!")
        if process.poll() is None:
            process.kill()
        return None

    print("Server started successfully\n")
    return process


def stop_server(process):
    if process:
        print("\nStopping server...")
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=10)
            print("Server stopped\n")
        except subprocess.TimeoutExpired:
            print("Server didn't stop gracefully, forcing...")
            process.kill()
            process.wait()


def run_tests(test_args=None):
    cmd = [sys.executable, "-m", "pytest"]

    if test_args:
        cmd.extend(test_args)
    else:
        cmd.extend([
            "-c", "tests/pytest.ini",
            "tests/",
            "-v",
            "--tb=short",
            "--color=yes"
        ])

    print_banner("Running Tests")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    print_banner("CloudflareBypassForScraping Test Suite")

    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        print("pytest is not installed!")
        print("Install test requirements with: pip install -r tests/test-requirements.txt")
        return 1

    server_process = None

    try:
        server_process = start_server()
        if not server_process:
            return 1

        test_args = sys.argv[1:] if len(sys.argv) > 1 else None
        exit_code = run_tests(test_args)

        print_banner("Test Results")
        if exit_code == 0:
            print("All tests passed!\n")
        else:
            print(f"Tests failed with exit code {exit_code}\n")

        return exit_code

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 130

    except Exception as e:
        print(f"\nError running tests: {e}")
        return 1

    finally:
        stop_server(server_process)


if __name__ == "__main__":
    sys.exit(main())
