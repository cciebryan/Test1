# Network MCP Server

This project provides a Network MCP Server that gives Claude direct access to networking tools for device management, diagnostics, and monitoring.

## MCP Tools Available

When the `network-mcp` MCP server is connected, you have access to these tools:

### Diagnostics
- `tool_ping` — Ping a host to check reachability and RTT
- `tool_traceroute` — Trace the network path to a host
- `tool_dns_lookup` — Look up DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR)
- `tool_port_scan` — Scan TCP ports on a host to find open services
- `tool_whois` — WHOIS registration lookup for domains/IPs
- `tool_network_interfaces` — List local network interfaces and IPs

### Monitoring
- `tool_check_host` — Quick reachability check for a single host
- `tool_measure_latency` — Measure latency with min/avg/max/stddev stats
- `tool_check_tcp_service` — Check if a TCP service is responding, grab its banner
- `tool_check_http` — Check HTTP/HTTPS endpoint health
- `tool_multi_host_check` — Check multiple hosts in parallel

### Device Management
- `tool_ssh_execute` — Execute a command on a remote device via SSH
- `tool_ssh_get_config` — Retrieve running config from a network device (supports linux, cisco_ios, cisco_nxos, juniper, arista)
- `tool_snmp_get` — Query a single SNMP OID
- `tool_snmp_walk` — Walk an SNMP OID tree

## Usage Notes

- Use the MCP tools directly for all network operations — do not shell out with Bash when an MCP tool exists for the task.
- For SSH, always ask the user for credentials if not already provided. Never guess or reuse credentials without confirmation.
- The SessionStart hook in `.claude/settings.json` auto-installs the package so the MCP server is available each session.
