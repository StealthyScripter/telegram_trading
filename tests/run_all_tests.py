import importlib.util
from pathlib import Path
import subprocess
import sys


def main():
    include_integration = "--include-integration" in sys.argv
    paths = [
        arg for arg in sys.argv[1:]
        if arg != "--include-integration"
    ]
    python_executable = sys.executable

    if importlib.util.find_spec("pytest") is None:
        venv_python = Path(__file__).resolve().parents[1] / "venv" / "bin" / "python"
        if venv_python.exists():
            python_executable = str(venv_python)

    command = [
        python_executable,
        "-m",
        "pytest",
        "-s",
        *(paths or ["tests"]),
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
