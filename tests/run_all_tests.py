import subprocess
import sys


def main():
    include_integration = "--include-integration" in sys.argv

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-s",
        "tests",
    ]

    if not include_integration:
        command.extend(["-m", "not integration"])

    result = subprocess.run(command)

    if result.returncode != 0:
        print("\nSome tests failed.")
        sys.exit(result.returncode)

    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
