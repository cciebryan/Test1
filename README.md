# Network MCP Server

An MCP (Model Context Protocol) server that gives AI assistants powerful networking tools — diagnostics, monitoring, and device management.

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io) is an open standard that lets AI assistants call external tools. This server exposes networking capabilities that Claude (or any MCP client) can use.

## Tools

### Diagnostics
| Tool | Description |
|------|-------------|
| `tool_ping` | Ping a host to check reachability and RTT |
| `tool_traceroute` | Trace the network path to a host |
| `tool_dns_lookup` | Look up DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR) |
| `tool_port_scan` | Scan TCP ports for open services |
| `tool_whois` | WHOIS lookup for domains and IPs |
| `tool_network_interfaces` | List local network interfaces |

### Monitoring
| Tool | Description |
|------|-------------|
| `tool_check_host` | Quick reachability check for a single host |
| `tool_measure_latency` | Latency stats (min/avg/max/stddev) |
| `tool_check_tcp_service` | Check if a TCP service is responding + banner grab |
| `tool_check_http` | HTTP(S) endpoint health check |
| `tool_multi_host_check` | Check multiple hosts in parallel |

### Device Management
| Tool | Description |
|------|-------------|
| `tool_ssh_execute` | Run a command on a remote device via SSH |
| `tool_ssh_get_config` | Get running config (Linux, Cisco, Juniper, Arista) |
| `tool_snmp_get` | Query a single SNMP OID |
| `tool_snmp_walk` | Walk an SNMP OID tree |

## Installation

```bash
# Clone the repo
git clone https://github.com/cciebryan/Test1.git
cd Test1

# Install
pip install -e .

# Install with dev/test dependencies
pip install -e ".[dev]"
```

## Usage

### With Claude Desktop

Add this to your Claude Desktop config (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "network": {
      "command": "python",
      "args": ["-m", "network_mcp"],
      "env": {}
    }
  }
}
```

Then restart Claude Desktop. You'll see the networking tools available in your tool list.

### With the MCP CLI

```bash
# Run directly
python -m network_mcp

# Or via the MCP CLI
mcp run src/network_mcp/server.py
```

### Standalone (for testing)

```bash
# Install in development mode
pip install -e .

# Run the server
network-mcp
```

## Architecture

```
src/network_mcp/
├── __init__.py            # Package metadata
├── __main__.py            # Entry point for `python -m network_mcp`
├── server.py              # MCP server — registers all tools
├── diagnostics.py         # ping, traceroute, DNS, port scan, whois
├── monitoring.py          # host checks, latency, service monitoring
└── device_management.py   # SSH execution, config retrieval, SNMP
```

**Key design decisions:**
- **Async throughout** — all tools are async, so the server stays responsive
- **System commands where possible** — uses `ping`, `traceroute`, `curl`, `whois` for reliability
- **Paramiko for SSH** — mature library for device management
- **dnspython for DNS** — full DNS record type support
- **No root required** — works with standard user permissions (except raw ICMP)

## Requirements

- Python 3.10+
- System tools: `ping`, `traceroute`, `curl`, `whois` (usually pre-installed on Linux/macOS)
- Optional: `snmpget`/`snmpwalk` for SNMP tools (install via `apt install snmp` or `brew install net-snmp`)

## How MCP Works (For Beginners)

```
┌──────────────┐         MCP Protocol          ┌──────────────────┐
│              │  ◄──── tool discovery ────►   │                  │
│  MCP Client  │                                │  MCP Server      │
│  (Claude)    │  ── call tool_ping("8.8.8.8") ──►  (this code)  │
│              │  ◄── { "success": true, ... } ──  │              │
└──────────────┘                                └──────────────────┘
```

1. **Discovery** — Claude asks the server "what tools do you have?"
2. **The server responds** with a list of tools and their schemas
3. **Claude calls a tool** when it's relevant to the user's question
4. **The server executes** the tool and returns JSON results
5. **Claude interprets** the results and presents them to the user

The transport can be **stdio** (Claude Desktop launches the server as a subprocess) or **HTTP+SSE** (server runs independently).
