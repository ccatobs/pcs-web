#!/usr/bin/env python3
"""Start mock OCS agents for ocs-web development.

This script manages the lifecycle of mock OCS agents used for developing
and testing the ocs-web interface without requiring real hardware.

Usage
-----
1. Start crossbar:

       docker compose up -d

2. Activate virtual environment:

       source .venv/bin/activate  # Linux/macOS
       .venv\\Scripts\\activate   # Windows

3. Edit configuration::

       mock-agents.yaml

4. Run the script:

       python start_mock_agents.py

Configuration is read from mock-agents.yaml by default. The script should
be run from the dev/ directory.

"""

import argparse
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import yaml


# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_AGENT_DIR_NOT_FOUND = 2
EXIT_NO_AGENTS = 3
EXIT_USER_ABORT = 130

# Directory structure (relative to this script in dev/)
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_AGENT_DIR = SCRIPT_DIR.parent / "agent"
DEFAULT_CONFIG_FILE = SCRIPT_DIR / "mock-agents.yaml"

# Excluded YAML files (not agent definitions)
EXCLUDED_YAML_FILES = frozenset({"config.yaml", "site-config.yaml"})

# Timeouts
SOCKET_TIMEOUT = 2.0
PROCESS_TERMINATE_TIMEOUT = 5.0

# Configure module logger
log = logging.getLogger(__name__)


def make_parser():
    """Create the argument parser for the mock agent launcher.

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser.

    """
    parser = argparse.ArgumentParser(
        description="Start mock OCS agents for ocs-web development.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=DEFAULT_CONFIG_FILE,
        metavar="PATH",
        help="Path to config file (default: %(default)s)",
    )

    parser.add_argument(
        "--agent-dir",
        type=Path,
        default=DEFAULT_AGENT_DIR,
        metavar="PATH",
        help="Path to agent directory (default: %(default)s)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_agents",
        help="List available mock agents and exit",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: %(default)s)",
    )

    return parser


def configure_logging(level_name):
    """Configure logging for the application.

    Parameters
    ----------
    level_name : str
        Logging level name (DEBUG, INFO, WARNING, ERROR).

    """
    level = getattr(logging, level_name)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def discover_agents(agent_dir):
    """Discover available agent YAML files in the agent directory.

    Parameters
    ----------
    agent_dir : Path
        Path to the directory containing agent YAML files.

    Returns
    -------
    list of str
        Sorted list of agent YAML filenames.

    """
    if not agent_dir.exists():
        log.warning("Agent directory does not exist: %s", agent_dir)
        return []

    agents = [
        f.name for f in agent_dir.glob("*.yaml") if f.name not in EXCLUDED_YAML_FILES
    ]

    log.debug("Discovered %d agent(s) in %s", len(agents), agent_dir)
    return sorted(agents)


def load_config(config_path):
    """Load and validate configuration from YAML file.

    Parameters
    ----------
    config_path : Path
        Path to the configuration YAML file.

    Returns
    -------
    dict
        Validated configuration dictionary.

    Raises
    ------
    SystemExit
        If configuration is missing or invalid.

    """
    if not config_path.exists():
        log.error("Config file not found: %s", config_path)
        log.error("Please create a config file. See README.md for format.")
        sys.exit(EXIT_CONFIG_ERROR)

    log.debug("Loading config from %s", config_path)

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Validate crossbar section
    if "crossbar" not in config:
        log.error("Missing 'crossbar' section in %s", config_path)
        sys.exit(EXIT_CONFIG_ERROR)

    required_fields = ("url", "realm", "address_root")
    for field in required_fields:
        if field not in config["crossbar"]:
            log.error("Missing 'crossbar.%s' in %s", field, config_path)
            sys.exit(EXIT_CONFIG_ERROR)

    # Validate agents section
    if not config.get("agents"):
        log.error("Missing or empty 'agents' list in %s", config_path)
        sys.exit(EXIT_CONFIG_ERROR)

    return config


def check_crossbar_connection(url):
    """Check if crossbar router is reachable.

    Parameters
    ----------
    url : str
        WebSocket URL of the crossbar router.

    Returns
    -------
    bool
        True if crossbar is reachable, False otherwise.

    """
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8001

    log.debug("Checking crossbar connection at %s:%d", host, port)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            result = sock.connect_ex((host, port))
            return result == 0

    except socket.timeout:
        log.warning("Connection to %s:%d timed out", host, port)
        return False

    except socket.gaierror as exc:
        log.warning("Failed to resolve hostname '%s': %s", host, exc)
        return False

    except OSError as exc:
        log.warning("Network error connecting to %s:%d: %s", host, port, exc)
        return False


def start_agent_process(
    agent_script, agent_yaml, crossbar_url, realm, address_root, env
):
    """Start a single mock agent process.

    Parameters
    ----------
    agent_script : Path
        Path to agent.py script.
    agent_yaml : str
        Name of the agent YAML file.
    crossbar_url : str
        WebSocket URL for crossbar connection.
    realm : str
        WAMP realm name.
    address_root : str
        OCS address root.
    env : dict
        Environment variables for the subprocess.

    Returns
    -------
    subprocess.Popen
        The started process.

    """
    yaml_path = agent_script.parent / agent_yaml

    cmd = [
        sys.executable,
        str(agent_script),
        "--site-host",
        "none",
        "--site-hub",
        crossbar_url,
        "--site-realm",
        realm,
        "--address-root",
        address_root,
        "--schema-file",
        str(yaml_path),
    ]

    log.debug("Starting process: %s", " ".join(cmd))

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )


def start_agents(agent_dir, agents, crossbar_url, realm, address_root):
    """Start mock agent processes.

    Parameters
    ----------
    agent_dir : Path
        Path to the directory containing agent files.
    agents : list of str
        List of agent YAML filenames to start.
    crossbar_url : str
        WebSocket URL for crossbar connection.
    realm : str
        WAMP realm name.
    address_root : str
        OCS address root.

    Returns
    -------
    list of tuple
        List of (agent_name, process) tuples.

    """
    agent_script = agent_dir / "agent.py"

    if not agent_script.exists():
        log.error("agent.py not found at %s", agent_script)
        sys.exit(EXIT_AGENT_DIR_NOT_FOUND)

    # Prepare environment
    env = os.environ.copy()
    env["OCS_CONFIG_DIR"] = str(SCRIPT_DIR / "ocs-config")

    processes = []

    for agent_yaml in agents:
        yaml_path = agent_dir / agent_yaml

        if not yaml_path.exists():
            log.warning("Agent file not found, skipping: %s", agent_yaml)
            continue

        log.info("Starting %s", agent_yaml)

        proc = start_agent_process(
            agent_script, agent_yaml, crossbar_url, realm, address_root, env
        )
        processes.append((agent_yaml, proc))

    return processes


def handle_dead_agent(name, proc):
    """Handle and report a dead agent process.

    Parameters
    ----------
    name : str
        Name of the agent.
    proc : subprocess.Popen
        The dead process.

    """
    log.warning("Agent %s exited with code %d", name, proc.returncode)

    if proc.stdout:
        output = proc.stdout.read()
        if output:
            for line in output.strip().split("\n"):
                log.warning("  %s: %s", name, line)


def monitor_processes(processes):
    """Monitor running agent processes until all exit or interrupted.

    Parameters
    ----------
    processes : list of tuple
        List of (agent_name, process) tuples to monitor.

    """
    reported_dead = set()

    try:
        while True:
            alive_count = 0

            for name, proc in processes:
                # Check if process is still running
                if proc.poll() is None:
                    alive_count += 1
                    continue

                # Process has exited
                if name not in reported_dead:
                    reported_dead.add(name)
                    handle_dead_agent(name, proc)

            if alive_count == 0:
                log.info("All agents have exited")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        log.info("Received interrupt signal")
        shutdown_agents(processes)


def shutdown_agents(processes):
    """Gracefully shutdown all agent processes.

    Parameters
    ----------
    processes : list of tuple
        List of (agent_name, process) tuples to shutdown.

    """
    log.info("Shutting down %d agent(s)...", len(processes))

    # Send SIGTERM to all processes
    for name, proc in processes:
        if proc.poll() is None:
            log.debug("Terminating %s", name)
            proc.terminate()

    # Wait for graceful shutdown
    for name, proc in processes:
        try:
            proc.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
            log.debug("%s terminated", name)
        except subprocess.TimeoutExpired:
            log.warning("%s did not terminate, killing", name)
            proc.kill()

    log.info("Shutdown complete")


def print_agent_list(agent_dir, agents):
    """Print list of available agents.

    Parameters
    ----------
    agent_dir : Path
        Path to the agent directory.
    agents : list of str
        List of available agent filenames.

    """
    print(f"Agent directory: {agent_dir}")
    print(f"\nAvailable mock agents ({len(agents)}):")

    for agent in agents:
        print(f"  - {agent}")


def main():
    """Main entry point for the mock agent launcher."""
    parser = make_parser()
    args = parser.parse_args()

    configure_logging(args.log_level)

    # Resolve paths
    agent_dir = args.agent_dir.resolve()
    config_path = args.config
    if not config_path.is_absolute():
        config_path = SCRIPT_DIR / config_path

    # Validate agent directory
    if not agent_dir.exists():
        log.error("Agent directory not found: %s", agent_dir)
        log.error("Make sure you're running from the dev/ directory")
        sys.exit(EXIT_AGENT_DIR_NOT_FOUND)

    # Discover available agents
    available_agents = discover_agents(agent_dir)

    # Handle --list flag
    if args.list_agents:
        print_agent_list(agent_dir, available_agents)
        sys.exit(EXIT_SUCCESS)

    # Load configuration
    config = load_config(config_path)

    crossbar_url = config["crossbar"]["url"]
    realm = config["crossbar"]["realm"]
    address_root = config["crossbar"]["address_root"]
    agents = config["agents"]

    # Validate configured agents
    invalid_agents = [a for a in agents if a not in available_agents]
    if invalid_agents:
        log.warning("Configured agents not found: %s", invalid_agents)
        agents = [a for a in agents if a in available_agents]

    if not agents:
        log.error("No valid agents to start")
        sys.exit(EXIT_NO_AGENTS)

    # Log configuration summary
    log.info("Config file: %s", config_path)
    log.info("Agent directory: %s", agent_dir)
    log.info("Crossbar URL: %s", crossbar_url)
    log.info("Realm: %s", realm)
    log.info("Address root: %s", address_root)
    log.info("Agents: %d configured, %d available", len(agents), len(available_agents))

    # Check crossbar connection
    log.info("Checking crossbar connection...")

    if not check_crossbar_connection(crossbar_url):
        log.warning("Cannot connect to crossbar at %s", crossbar_url)
        log.warning("Make sure crossbar is running: docker compose up -d")

        try:
            response = input("Continue anyway? [y/N] ")
            if response.lower() != "y":
                sys.exit(EXIT_USER_ABORT)
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(EXIT_USER_ABORT)
    else:
        log.info("Crossbar is reachable")

    # Start agents
    processes = start_agents(
        agent_dir=agent_dir,
        agents=agents,
        crossbar_url=crossbar_url,
        realm=realm,
        address_root=address_root,
    )

    if not processes:
        log.error("No agents started")
        sys.exit(EXIT_NO_AGENTS)

    log.info("%d agent(s) started. Press Ctrl+C to stop.", len(processes))

    # Monitor until exit
    monitor_processes(processes)


if __name__ == "__main__":
    main()
