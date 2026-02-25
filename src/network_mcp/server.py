"""
Network MCP Server
==================
An MCP server that exposes networking tools to AI assistants.

Tools provided:
  Diagnostics:  ping, traceroute, dns_lookup, port_scan, whois, network_interfaces
  Monitoring:   check_host, measure_latency, check_tcp_service, check_http, multi_host_check
  Device Mgmt:  ssh_execute, ssh_get_config, snmp_get, snmp_walk

Run with:
    python -m network_mcp.server          # stdio transport (for Claude Desktop)
    mcp run src/network_mcp/server.py     # also works via MCP CLI
"""

import json

from mcp.server.fastmcp import FastMCP

from network_mcp.diagnostics import (
    dns_lookup,
    get_network_interfaces,
    ping,
    port_scan,
    traceroute,
    whois_lookup,
)
from network_mcp.monitoring import (
    check_host,
    check_http_endpoint,
    check_tcp_service,
    measure_latency,
    multi_host_check,
)
from network_mcp.device_management import (
    snmp_get,
    snmp_walk,
    ssh_execute,
    ssh_get_config,
)

# ---------------------------------------------------------------------------
# Create the MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Network MCP Server",
    instructions="Networking tools: diagnostics, monitoring, and device management",
)


# ===========================================================================
#  DIAGNOSTIC TOOLS
# ===========================================================================


@mcp.tool()
async def tool_ping(host: str, count: int = 4, timeout: float = 2.0) -> str:
    """Ping a host to check reachability and measure round-trip time.

    Args:
        host: Hostname or IP address to ping (e.g., '8.8.8.8' or 'google.com').
        count: Number of ping packets to send (default 4).
        timeout: Seconds to wait per packet (default 2).
    """
    result = await ping(host, count, timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_traceroute(host: str, max_hops: int = 30) -> str:
    """Trace the network path to a host, showing each hop along the route.

    Args:
        host: Hostname or IP address to trace.
        max_hops: Maximum number of hops to trace (default 30).
    """
    result = await traceroute(host, max_hops)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_dns_lookup(
    name: str,
    record_type: str = "A",
    server: str | None = None,
) -> str:
    """Look up DNS records for a domain name.

    Args:
        name: Domain name to look up (e.g., 'example.com').
        record_type: DNS record type — A, AAAA, MX, NS, TXT, CNAME, SOA, or PTR.
        server: Optional DNS server IP to query (e.g., '8.8.8.8').
    """
    result = await dns_lookup(name, record_type, server)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_port_scan(
    host: str,
    ports: list[int] | None = None,
    timeout: float = 1.0,
) -> str:
    """Scan TCP ports on a host to find open services.

    Args:
        host: Hostname or IP address to scan.
        ports: Specific port numbers to check. Defaults to common ports
               (22, 80, 443, 3306, etc.).
        timeout: Seconds to wait per port (default 1).
    """
    result = await port_scan(host, ports, timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_whois(target: str) -> str:
    """Look up WHOIS registration information for a domain or IP address.

    Args:
        target: Domain name or IP address to look up.
    """
    result = await whois_lookup(target)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_network_interfaces() -> str:
    """List local network interfaces and their IP addresses."""
    result = await get_network_interfaces()
    return json.dumps(result, indent=2)


# ===========================================================================
#  MONITORING TOOLS
# ===========================================================================


@mcp.tool()
async def tool_check_host(host: str, timeout: float = 5.0) -> str:
    """Quick check whether a single host is reachable.

    Args:
        host: Hostname or IP address.
        timeout: Seconds to wait (default 5).
    """
    result = await check_host(host, timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_measure_latency(host: str, samples: int = 10) -> str:
    """Measure network latency to a host with statistics (min/avg/max/stddev).

    Args:
        host: Hostname or IP address.
        samples: Number of measurements (default 10).
    """
    result = await measure_latency(host, samples)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_check_tcp_service(
    host: str,
    port: int,
    timeout: float = 5.0,
    send_data: str | None = None,
) -> str:
    """Check if a TCP service is responding and optionally grab its banner.

    Args:
        host: Hostname or IP address.
        port: TCP port number (e.g., 22 for SSH, 80 for HTTP).
        timeout: Connection timeout in seconds (default 5).
        send_data: Optional string to send after connecting (for protocols
                   that need a request before returning a banner).
    """
    result = await check_tcp_service(host, port, timeout, send_data)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_check_http(
    url: str,
    method: str = "GET",
    timeout: float = 10.0,
    expected_status: int = 200,
) -> str:
    """Check if an HTTP/HTTPS endpoint is healthy.

    Args:
        url: Full URL to check (e.g., 'https://example.com/health').
        method: HTTP method — GET, HEAD, POST, etc. (default GET).
        timeout: Request timeout in seconds (default 10).
        expected_status: Expected HTTP status code for a healthy response (default 200).
    """
    result = await check_http_endpoint(url, method, timeout, expected_status)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_multi_host_check(hosts: list[str], timeout: float = 5.0) -> str:
    """Check reachability of multiple hosts in parallel.

    Args:
        hosts: List of hostnames or IP addresses to check.
        timeout: Seconds to wait per host (default 5).
    """
    result = await multi_host_check(hosts, timeout)
    return json.dumps(result, indent=2)


# ===========================================================================
#  DEVICE MANAGEMENT TOOLS
# ===========================================================================


@mcp.tool()
async def tool_ssh_execute(
    host: str,
    username: str,
    command: str,
    port: int = 22,
    password: str | None = None,
    key_path: str | None = None,
    timeout: float = 30.0,
) -> str:
    """Execute a command on a remote device via SSH.

    Args:
        host: Hostname or IP of the target device.
        username: SSH username.
        command: Shell command to run on the remote device.
        port: SSH port (default 22).
        password: SSH password (omit if using key-based auth).
        key_path: Path to an SSH private key file.
        timeout: Connection timeout in seconds (default 30).
    """
    result = await ssh_execute(host, username, command, port, password, key_path, timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_ssh_get_config(
    host: str,
    username: str,
    device_type: str = "linux",
    port: int = 22,
    password: str | None = None,
    key_path: str | None = None,
) -> str:
    """Retrieve the running configuration from a network device via SSH.

    Args:
        host: Hostname or IP of the device.
        username: SSH username.
        device_type: Device type — 'linux', 'cisco_ios', 'cisco_nxos', 'juniper', or 'arista'.
        port: SSH port (default 22).
        password: SSH password.
        key_path: Path to SSH private key file.
    """
    result = await ssh_get_config(host, username, device_type, port, password, key_path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_snmp_get(
    host: str,
    oid: str,
    community: str = "public",
    port: int = 161,
) -> str:
    """Query a single SNMP OID on a network device.

    Args:
        host: Hostname or IP of the device.
        oid: SNMP OID to query (e.g., '1.3.6.1.2.1.1.1.0' for sysDescr).
        community: SNMP community string (default 'public').
        port: SNMP port (default 161).
    """
    result = await snmp_get(host, oid, community, port)
    return json.dumps(result, indent=2)


@mcp.tool()
async def tool_snmp_walk(
    host: str,
    oid: str,
    community: str = "public",
    port: int = 161,
) -> str:
    """Walk an SNMP OID tree on a network device, returning all entries.

    Args:
        host: Hostname or IP of the device.
        oid: Base OID to walk (e.g., '1.3.6.1.2.1.1' for system info).
        community: SNMP community string (default 'public').
        port: SNMP port (default 161).
    """
    result = await snmp_walk(host, oid, community, port)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Run the Network MCP Server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
