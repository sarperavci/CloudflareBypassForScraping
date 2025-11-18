#!/usr/bin/env python3
"""
Runs all tests
"""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path


def print_banner(text):
    """Print a formatted banner."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def start_server():
    """Start the server in the background."""
    print("Starting server...")
    
    # Start server process
    process = subprocess.Popen(
        [sys.executable, "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent
    )
    
    # Wait for server to start
    print("⏳ Waiting for server to initialize...")
    time.sleep(5)
    
    # Check if server started successfully
    if process.poll() is not None:
        print("❌ Server failed to start!")
        return None
    
    print("✅ Server started successfully\n")
    return process


def stop_server(process):
    """Stop the server process."""
    if process:
        print("\n🛑 Stopping server...")
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=10)
            print("✅ Server stopped\n")
        except subprocess.TimeoutExpired:
            print("⚠️ Server didn't stop gracefully, forcing...")
            process.kill()
            process.wait()


def run_tests(test_args=None):
    """Run pytest with specified arguments."""
    cmd = [sys.executable, "-m", "pytest"]
    
    if test_args:
        cmd.extend(test_args)
    else:
        # Default: run all tests with verbose output
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
    """Main test runner."""
    print_banner("CloudflareBypassForScraping Test Suite")
    
    # Check if pytest is installed
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
        # Start server
        server_process = start_server()
        if not server_process:
            return 1
        
        # Run tests
        test_args = sys.argv[1:] if len(sys.argv) > 1 else None
        exit_code = run_tests(test_args)
        
        # Print summary
        print_banner("Test Results")
        if exit_code == 0:
            print("All tests passed!\n")
        else:
            print(f"Tests failed with exit code {exit_code}\n")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n\n Tests interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n Error running tests: {e}")
        return 1
        
    finally:
        # Always stop the server
        stop_server(server_process)


if __name__ == "__main__":
    sys.exit(main())
