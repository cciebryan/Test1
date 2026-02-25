"""Network monitoring tools: host checks, latency measurement, service availability."""

import asyncio
import time


async def check_host(host: str, timeout: float = 5.0) -> dict:
    """Check if a host is reachable (single ping).

    Args:
        host: Hostname or IP address.
        timeout: Timeout in seconds.

    Returns:
        Dict with host reachability status.
    """
    cmd = ["ping", "-c", "1", "-W", str(int(timeout)), host]
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    elapsed = round((time.monotonic() - start) * 1000, 2)

    return {
        "host": host,
        "reachable": proc.returncode == 0,
        "response_time_ms": elapsed if proc.returncode == 0 else None,
    }


async def measure_latency(host: str, samples: int = 10) -> dict:
    """Measure latency to a host over multiple samples.

    Args:
        host: Hostname or IP address.
        samples: Number of measurements to take.

    Returns:
        Dict with min/avg/max/stddev latency statistics.
    """
    cmd = ["ping", "-c", str(samples), "-i", "0.2", host]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode()

    result = {
        "host": host,
        "samples": samples,
        "success": proc.returncode == 0,
    }

    # Parse the rtt min/avg/max/mdev line
    for line in output.splitlines():
        if "rtt" in line or "round-trip" in line:
            # Format: rtt min/avg/max/mdev = 1.234/5.678/9.012/3.456 ms
            parts = line.split("=")
            if len(parts) == 2:
                values = parts[1].strip().split("/")
                if len(values) >= 4:
                    result["min_ms"] = float(values[0])
                    result["avg_ms"] = float(values[1])
                    result["max_ms"] = float(values[2])
                    result["stddev_ms"] = float(values[3].split()[0])
        if "packet loss" in line:
            result["summary"] = line.strip()

    return result


async def check_tcp_service(
    host: str,
    port: int,
    timeout: float = 5.0,
    send_data: str | None = None,
) -> dict:
    """Check if a TCP service is responding.

    Args:
        host: Hostname or IP address.
        port: TCP port number.
        timeout: Connection timeout in seconds.
        send_data: Optional data to send after connecting (for banner grabbing).

    Returns:
        Dict with service status and optional banner.
    """
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        elapsed = round((time.monotonic() - start) * 1000, 2)

        banner = None
        if send_data:
            writer.write(send_data.encode())
            await writer.drain()

        # Try to read a banner (many services send one on connect)
        try:
            data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            if data:
                banner = data.decode(errors="replace").strip()
        except asyncio.TimeoutError:
            pass

        writer.close()
        await writer.wait_closed()

        return {
            "host": host,
            "port": port,
            "status": "open",
            "response_time_ms": elapsed,
            "banner": banner,
        }
    except asyncio.TimeoutError:
        return {
            "host": host,
            "port": port,
            "status": "timeout",
            "response_time_ms": None,
        }
    except ConnectionRefusedError:
        return {
            "host": host,
            "port": port,
            "status": "refused",
            "response_time_ms": None,
        }
    except OSError as e:
        return {
            "host": host,
            "port": port,
            "status": "error",
            "error": str(e),
            "response_time_ms": None,
        }


async def check_http_endpoint(
    url: str,
    method: str = "GET",
    timeout: float = 10.0,
    expected_status: int = 200,
) -> dict:
    """Check if an HTTP(S) endpoint is healthy.

    Args:
        url: Full URL to check (e.g., https://example.com/health).
        method: HTTP method to use.
        timeout: Request timeout in seconds.
        expected_status: Expected HTTP status code.

    Returns:
        Dict with HTTP response status and timing.
    """
    # Use curl since it's available everywhere and avoids extra dependencies
    cmd = [
        "curl", "-s", "-o", "/dev/null",
        "-w", "%{http_code} %{time_total} %{size_download}",
        "-X", method,
        "--max-time", str(int(timeout)),
        "-L",  # follow redirects
        url,
    ]
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    elapsed = round((time.monotonic() - start) * 1000, 2)

    output = stdout.decode().strip()
    parts = output.split()

    result = {
        "url": url,
        "method": method,
        "total_time_ms": elapsed,
    }

    if parts:
        status_code = int(parts[0])
        result["status_code"] = status_code
        result["healthy"] = status_code == expected_status
        if len(parts) > 1:
            result["curl_time_s"] = float(parts[1])
        if len(parts) > 2:
            result["response_size_bytes"] = int(parts[2])
    else:
        result["healthy"] = False
        result["error"] = stderr.decode().strip() or "Unknown error"

    return result


async def multi_host_check(hosts: list[str], timeout: float = 5.0) -> dict:
    """Check reachability of multiple hosts in parallel.

    Args:
        hosts: List of hostnames or IP addresses.
        timeout: Timeout per host.

    Returns:
        Dict with results for each host.
    """
    tasks = [check_host(h, timeout) for h in hosts]
    results = await asyncio.gather(*tasks)

    reachable = [r for r in results if r["reachable"]]
    unreachable = [r for r in results if not r["reachable"]]

    return {
        "total": len(hosts),
        "reachable_count": len(reachable),
        "unreachable_count": len(unreachable),
        "results": list(results),
    }
