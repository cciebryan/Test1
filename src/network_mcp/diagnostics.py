"""Network diagnostic tools: ping, traceroute, DNS lookup, port scan, whois."""

import asyncio
import socket
import struct
import time

import dns.resolver
import dns.reversename


async def ping(host: str, count: int = 4, timeout: float = 2.0) -> dict:
    """Ping a host using the system ping command.

    Args:
        host: Hostname or IP address to ping.
        count: Number of ping packets to send.
        timeout: Timeout in seconds per packet.

    Returns:
        Dict with ping results including packet loss and round-trip times.
    """
    cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), host]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    output = stdout.decode()
    result = {
        "host": host,
        "success": proc.returncode == 0,
        "output": output,
    }

    # Parse summary line (e.g., "4 packets transmitted, 4 received, 0% packet loss")
    for line in output.splitlines():
        if "packet loss" in line:
            result["summary"] = line.strip()
        if "rtt" in line or "round-trip" in line:
            result["rtt"] = line.strip()

    if stderr.decode().strip():
        result["error"] = stderr.decode().strip()

    return result


async def traceroute(host: str, max_hops: int = 30) -> dict:
    """Run traceroute to a host.

    Args:
        host: Hostname or IP address to trace.
        max_hops: Maximum number of hops.

    Returns:
        Dict with traceroute output.
    """
    cmd = ["traceroute", "-m", str(max_hops), "-w", "2", host]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    return {
        "host": host,
        "success": proc.returncode == 0,
        "output": stdout.decode(),
        "error": stderr.decode().strip() or None,
    }


async def dns_lookup(
    name: str,
    record_type: str = "A",
    server: str | None = None,
) -> dict:
    """Perform a DNS lookup.

    Args:
        name: Domain name to look up.
        record_type: DNS record type (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR).
        server: Optional DNS server to query.

    Returns:
        Dict with DNS records found.
    """
    resolver = dns.resolver.Resolver(configure=False)
    if server:
        resolver.nameservers = [server]
    else:
        # Try to read system config; fall back to well-known public DNS
        try:
            resolver.read_resolv_conf("/etc/resolv.conf")
        except Exception:
            resolver.nameservers = ["8.8.8.8", "1.1.1.1"]

    record_type = record_type.upper()
    results = {"name": name, "record_type": record_type, "records": []}

    try:
        if record_type == "PTR":
            rev_name = dns.reversename.from_address(name)
            answers = resolver.resolve(rev_name, "PTR")
        else:
            answers = resolver.resolve(name, record_type)

        for rdata in answers:
            record = {"value": str(rdata), "ttl": answers.ttl}
            if record_type == "MX":
                record["priority"] = rdata.preference
            results["records"].append(record)

        results["success"] = True
    except dns.resolver.NXDOMAIN:
        results["success"] = False
        results["error"] = f"Domain '{name}' does not exist (NXDOMAIN)"
    except dns.resolver.NoAnswer:
        results["success"] = False
        results["error"] = f"No {record_type} records found for '{name}'"
    except dns.resolver.NoNameservers:
        results["success"] = False
        results["error"] = "No nameservers available to answer the query"
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return results


async def port_scan(
    host: str,
    ports: list[int] | None = None,
    timeout: float = 1.0,
) -> dict:
    """Scan TCP ports on a host.

    Args:
        host: Hostname or IP address to scan.
        ports: List of ports to scan. Defaults to common ports.
        timeout: Connection timeout in seconds per port.

    Returns:
        Dict with open/closed port information.
    """
    if ports is None:
        # Common well-known ports
        ports = [
            21, 22, 23, 25, 53, 80, 110, 143, 443, 445,
            993, 995, 3306, 3389, 5432, 6379, 8080, 8443,
        ]

    # Well-known port service names
    common_services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
        443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
        3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
        6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    }

    async def check_port(port: int) -> dict:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            return {
                "port": port,
                "state": "open",
                "service": common_services.get(port, "unknown"),
            }
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return {
                "port": port,
                "state": "closed",
                "service": common_services.get(port, "unknown"),
            }

    tasks = [check_port(p) for p in sorted(ports)]
    port_results = await asyncio.gather(*tasks)

    open_ports = [r for r in port_results if r["state"] == "open"]
    closed_ports = [r for r in port_results if r["state"] == "closed"]

    return {
        "host": host,
        "total_scanned": len(ports),
        "open_count": len(open_ports),
        "open_ports": open_ports,
        "closed_ports": closed_ports,
    }


async def whois_lookup(target: str) -> dict:
    """Perform a WHOIS lookup on a domain or IP.

    Args:
        target: Domain name or IP address.

    Returns:
        Dict with WHOIS information.
    """
    cmd = ["whois", target]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    return {
        "target": target,
        "success": proc.returncode == 0,
        "output": stdout.decode(),
        "error": stderr.decode().strip() or None,
    }


async def get_network_interfaces() -> dict:
    """Get local network interface information.

    Returns:
        Dict with network interface details.
    """
    cmd = ["ip", "-j", "addr", "show"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    # Fall back to plain output if JSON not supported
    if proc.returncode != 0:
        cmd = ["ip", "addr", "show"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

    return {
        "success": proc.returncode == 0,
        "output": stdout.decode(),
        "error": stderr.decode().strip() or None,
    }
