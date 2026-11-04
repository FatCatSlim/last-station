# Last Station

Last Station is a Python terminal simulation about managing a small station,
monitoring its systems and resources, and using a local AI adviser.

The project uses a simple client/server setup:

- `RAVEN-HUB` runs the main simulation state and API.
- `RAVEN-01` is the operator terminal and communicates with the Hub over HTTP.
- A local Ollama model acts as an adviser using facts calculated by Python.

Python handles the actual simulation rules and decisions. The AI adviser only
interprets the information it receives and gives suggestions.

## Project Status

Version 1 is complete. It includes the main simulation, terminal interface,
API, and local AI adviser.

Phase 2 is currently in development.

Phase 2.1 added automatic NORMAL or RATION cycles, with an ON/OFF option.
When AUTO mode is active, the operator menu shows only the option to disable it.
Manual controls become available again when AUTO is turned off.

More improvements are planned as Phase 2 continues.

## Project Background

Last Station began as a small Python survival simulation inspired by games like
Metro 2033 and by Frank Herbert's Dune. Over time, it evolved into a project
for learning systems, infrastructure, networking, and local AI integration.

The project is intentionally being built in stages. Version 1 runs locally and
establishes the basic simulation, API, operator terminal, persistent state, and
AI adviser.

One of the future goals is to move RAVEN-HUB onto a separate older PC and have
RAVEN-01 communicate with it over a local network. This will let me experiment
with real client/server deployment and explore more infrastructure and
networking ideas using hardware I already have.

The long-term idea is to keep Last Station as a practical environment for
learning and experimenting with systems and networking concepts. Some of those
technical systems may eventually connect more closely with the game side of the
project as it grows.

## Version 1 Features

- Terminal-based operator interface
- Resource monitoring for food, water, power, and scrap
- Normal and ration cycle modes
- Infrastructure status monitoring
- Generator degradation and repair system
- Expedition system with food, water, and scrap recovery
- Station warnings and condition states
- Recent cycle history
- Offline fallback using cached resource data
- Local AI adviser powered by Ollama
- Python handles the facts; the LLM interprets them and gives advice
- Static sector map for the RAVEN LINE

## Phase 2.1 — Automatic Cycles

Phase 2.1 introduced automatic NORMAL or RATION cycles with an ON/OFF option.

- Cycles advance automatically using a fixed timer.
- The operator selects NORMAL or RATION when enabling AUTO.
- While AUTO is running, the operator menu only allows disabling AUTO.
- Manual controls return when AUTO is turned off.
- Automatic cycles use the existing simulation logic.

## Architecture

```text
RAVEN-01 / main_pc/simulation.py
    |
    |-- HTTP through main_pc/tools.py
    |       |
    |       v
    |   RAVEN-HUB / FastAPI
    |   old_pc_hub/hub_api.py
    |       |
    |       v
    |   old_pc_hub/hub_state.json
    |
    |-- main_pc/cache.py
    |       |-- cache.json
    |       `-- cycle_history.json
    |
    `-- main_pc/agent_runner.py
            |
            v
        Ollama / last-station-adviser
```

`RAVEN-01` is the operator terminal. It talks to `RAVEN-HUB` over HTTP using
`main_pc/tools.py`.

`RAVEN-HUB` keeps the main simulation state and handles the actual simulation
logic. The local cache keeps recent data for things like offline fallback and
cycle history.

The Ollama adviser receives facts prepared by Python and gives suggestions, but
it does not directly control or change the simulation.

## Requirements

- Python 3.11+ (tested with Python 3.11)
- Ollama
- Windows PowerShell (used for the setup commands below)
- Ollama model: `qwen3.5:9b`

## Setup

Clone or download the project, then open PowerShell in the project root.

For example:

```powershell
cd "$HOME\Documents\last-station"
```

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Allow activation in the current PowerShell session

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

`-Scope Process` changes the execution policy only for the current PowerShell
session. Closing that PowerShell window removes the temporary change.

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

The prompt should now begin with `(.venv)`.

### 4. Install Python dependencies

```powershell
python -m pip install -r .\requirements.txt
```

The project currently uses:

- FastAPI
- Uvicorn
- Pydantic
- Requests

## Ollama Adviser Setup

Make sure Ollama is installed and running.

Open PowerShell and move to the project root:

```powershell
cd "$HOME\Documents\last-station"
```

### 1. Pull the base model

```powershell
ollama pull qwen3.5:9b
```

### 2. Build the Last Station adviser

From the project root:

```powershell
ollama create last-station-adviser -f .\Modelfile
```

The `Modelfile` gives the adviser its main role and general behavior.
More detailed Last Station rules are sent at runtime by
`main_pc/agent_runner.py`.

If the `Modelfile` is changed later, stop the currently loaded adviser and
rebuild it:

```powershell
ollama stop last-station-adviser
ollama create last-station-adviser -f .\Modelfile
```

## Running Last Station

Use two PowerShell terminals.

### Terminal 1 - Start RAVEN-HUB

Move to the project root:

```powershell
cd "$HOME\Documents\last-station"
```

Allow virtual environment activation in this PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Move into the Hub folder:

```powershell
cd .\old_pc_hub
```

Start RAVEN-HUB:

```powershell
uvicorn hub_api:app --reload
```

Uvicorn uses `127.0.0.1:8000` by default, so the Hub is available at:

```text
http://127.0.0.1:8000
```

The `--reload` option automatically restarts Uvicorn when Python source files
such as `hub_api.py` are changed.

RAVEN-HUB loads `hub_state.json` when the server starts. If `hub_state.json`
is edited manually while the Hub is running, stop Uvicorn with `Ctrl+C` and
start it again:

```powershell
uvicorn hub_api:app --reload
```

After manually changing `hub_state.json`, it is also a good idea to quit and
restart RAVEN-01 so the terminal reconnects and shows the updated Hub state.

### Terminal 2 - Start RAVEN-01

Move to the project root:

```powershell
cd "$HOME\Documents\last-station"
```

Allow virtual environment activation in this PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start the operator terminal:

```powershell
python .\main_pc\simulation.py
```

RAVEN-01 should connect to RAVEN-HUB and display the Last Station interface.

If `simulation.py` is changed, quit and restart RAVEN-01 for those code
changes to take effect.

## Main Operator Controls

```text
[1] Advance Normal Cycle   - Run the next cycle with normal resource use
[2] Advance Ration Cycle   - Run the next cycle using reduced food and water
[E] Expedition             - Send the expedition team to gather resources
[R] Engineering / Repair   - Check engineering status or start generator repair
[M] Sector Map             - View the current RAVEN LINE sector map
[L] Recent Cycle Log       - View the most recent cycle reports
[A] Ask Adviser            - Get advice from the local AI adviser
[T] Toggle Auto Mode       - Enable or disable automatic NORMAL/RATION cycles
[Q] Quit                   - Exit RAVEN-01
```

## AI Adviser Design

The AI adviser is kept separate from the actual simulation logic.

Python calculates the important facts, including:

- Current power state and trend
- Production state
- Resource changes and trends
- Repair availability and requirements
- Infrastructure status
- Expedition status

The local LLM uses those facts to give advice and point out what may need
attention. It does not calculate the simulation rules or directly change the
Hub state.

The basic idea is simple:

```text
Python / RAVEN-HUB = runs the simulation
LLM                = gives advice
```

## Project Structure

```text
last-station/
|-- .vscode/
|   `-- settings.json
|-- main_pc/
|   |-- agent_runner.py
|   |-- cache.py
|   |-- cache.json
|   |-- config.py
|   |-- cycle_history.json
|   |-- simulation.py
|   `-- tools.py
|-- old_pc_hub/
|   |-- hub_api.py
|   `-- hub_state.json
|-- .gitignore
|-- Modelfile
|-- README.md
|-- requirements.txt
`-- pyproject.toml
```

### Key Files

- `main_pc/simulation.py` - runs the RAVEN-01 terminal interface
- `main_pc/tools.py` - handles HTTP communication with RAVEN-HUB
- `main_pc/cache.py` - handles the local cache and recent cycle history
- `main_pc/agent_runner.py` - prepares adviser facts and talks to Ollama
- `main_pc/config.py` - stores the station name and Hub address
- `old_pc_hub/hub_api.py` - runs the FastAPI Hub and main simulation logic
- `old_pc_hub/hub_state.json` - stores the current Hub state
- `Modelfile` - sets up the local Ollama adviser
- `requirements.txt` - lists the Python packages the project needs
- `pyproject.toml` - stores the Black formatter settings

## Development Checks

Move to the project root:

```powershell
cd "$HOME\Documents\last-station"
```

To check the Python files for syntax errors:

```powershell
python -m compileall .\main_pc .\old_pc_hub
```

To review the imports used by the project while ignoring the virtual
environment:

```powershell
Get-ChildItem -Recurse -Filter *.py |
Where-Object { $_.FullName -notmatch '\\.venv\\' } |
Select-String -Pattern '^\s*(import|from)\s+'
```

Files and folders created automatically by Python, such as `.venv/`,
`__pycache__/`, and `.pyc` files, are ignored by Git through `.gitignore`.

## Planned Direction

Future development may include:

- Running RAVEN-HUB and RAVEN-01 on separate computers over a local network
- More realistic network, service, and system events
- Additional infrastructure and repair systems
- More monitoring and system-status tools
- Expanded interaction with the RAVEN LINE and game world
- More connections between the technical systems and the game side of Last Station

Version 1 is intentionally kept smaller so the main simulation, networking,
and AI adviser systems are easy to understand and build on before the project
gets more complex.
