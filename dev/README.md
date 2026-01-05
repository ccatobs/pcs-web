# PCS-Web Development Environment

This directory contains tools for developing pcs-web with mock OCS agents with no hardware requirements.

## Quick Start

### 1. One-time Setup

```bash
# From project root (pcs-web/)
cd dev

# Create Python virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Update frontend config (from project root)
cd ..
cp dev/public-config.json public/config.json
```

### 2. Configure Agents

Edit `mock-agents.yaml` to enable/disable agents:

```yaml
crossbar:
  url: "ws://localhost:8001/ws"
  realm: "test_realm"
  address_root: "observatory"

agents:
  - lakeshore240.yaml
  - lakeshore372.yaml
  # - acuagent.yaml  # uncomment to enable
```

See available agents:

```bash
python start_mock_agents.py --list
```

### 3. Start Development Environment

Run these from the `dev/` directory:

**Terminal 1 - Crossbar (WAMP router):**

```bash
cd dev
docker compose up
```

**Terminal 2 - Mock Agents:**

```bash
cd dev
python start_mock_agents.py
```

**Terminal 3 - Vue Dev Server (from project root):**

```bash
npm run serve
```

### 4. Open Browser

Navigate to <http://localhost:8080>

Select "Local Dev" from the dropdown. Agents should appear in the sidebar.

## Command Reference

```bash
# All commands run from dev/ directory

# List available agents (auto-discovered from ../agent/)
python start_mock_agents.py --list

# Start with default config (mock-agents.yaml)
python start_mock_agents.py

# Use different config file
python start_mock_agents.py --config my-test-config.yaml

# Specify different agent directory
python start_mock_agents.py --agent-dir /path/to/agents
```

## Creating Custom Mock Agents

Add a new YAML file in `../agent/`:

```yaml
agent_class: 'MyCustomAgent'
instance_id: 'my-agent-1'

processes:
  acq:
    startup: true  # Auto-start when agent launches
    data_settings:
      timestamp_field: 'timestamp'
    data:
      temperature: 25.5
      pressure: 101.3
      timestamp: 0  # Auto-updated every second

tasks:
  calibrate:
    run_time: 10  # Simulated duration in seconds
  reset: {}
```

The new agent will be auto-discovered. Add it to `mock-agents.yaml` to enable it.
