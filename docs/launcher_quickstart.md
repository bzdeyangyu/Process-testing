# Launcher Quickstart

## Windows quick start

1. Ensure Python 3 is installed.
2. Unzip the package.
3. Double-click `launch_process_testing.bat`.
4. Wait for the launcher to create a virtual environment, install dependencies, generate a mock demo run, and open `http://localhost:8765/`.

## What the launcher does

- creates a local virtual environment with `python -m venv`
- installs dependencies with `pip install -r requirements.txt`
- runs `demo/run_mvp.py --no-llm --image-provider mock` once if no board snapshot exists
- starts `server.py`
- opens the local dashboard in the browser
- keeps the architecture page inside the dashboard only via the `architecture.html` entry
- the batch file delegates to `process_testing_launcher.py`

## Packaging

To build the shareable archive again, run:

```bash
python package_process_testing.py
```

The archive will be created as `dist/Process-testing-launcher.zip`.
