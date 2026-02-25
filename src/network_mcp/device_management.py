"""Device management tools: SSH command execution and SNMP queries."""

import asyncio

import paramiko


async def ssh_execute(
    host: str,
    username: str,
    command: str,
    port: int = 22,
    password: str | None = None,
    key_path: str | None = None,
    timeout: float = 30.0,
) -> dict:
    """Execute a command on a remote device via SSH.

    Args:
        host: Hostname or IP of the target device.
        username: SSH username.
        command: Command to execute.
        port: SSH port (default 22).
        password: SSH password (if not using key auth).
        key_path: Path to SSH private key file.
        timeout: Connection timeout in seconds.

    Returns:
        Dict with command output, exit status, and any errors.
    """
    # Run the blocking paramiko call in a thread to keep async
    def _run_ssh():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": timeout,
        }
        if key_path:
            connect_kwargs["key_filename"] = key_path
        elif password:
            connect_kwargs["password"] = password

        try:
            client.connect(**connect_kwargs)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()

            return {
                "host": host,
                "command": command,
                "success": exit_status == 0,
                "exit_status": exit_status,
                "stdout": stdout.read().decode(errors="replace"),
                "stderr": stderr.read().decode(errors="replace"),
            }
        except paramiko.AuthenticationException:
            return {
                "host": host,
                "command": command,
                "success": False,
                "error": "Authentication failed",
            }
        except paramiko.SSHException as e:
            return {
                "host": host,
                "command": command,
                "success": False,
                "error": f"SSH error: {e}",
            }
        except Exception as e:
            return {
                "host": host,
                "command": command,
                "success": False,
                "error": str(e),
            }
        finally:
            client.close()

    return await asyncio.to_thread(_run_ssh)


async def ssh_get_config(
    host: str,
    username: str,
    device_type: str = "linux",
    port: int = 22,
    password: str | None = None,
    key_path: str | None = None,
) -> dict:
    """Retrieve the running configuration from a network device.

    This is a convenience wrapper that picks the right command
    based on the device type.

    Args:
        host: Hostname or IP of the device.
        username: SSH username.
        device_type: One of 'linux', 'cisco_ios', 'cisco_nxos', 'juniper', 'arista'.
        port: SSH port.
        password: SSH password.
        key_path: SSH private key path.

    Returns:
        Dict with the device configuration output.
    """
    config_commands = {
        "linux": "ip addr show && echo '---' && ip route show && echo '---' && cat /etc/resolv.conf",
        "cisco_ios": "show running-config",
        "cisco_nxos": "show running-config",
        "juniper": "show configuration",
        "arista": "show running-config",
    }

    command = config_commands.get(device_type)
    if not command:
        return {
            "host": host,
            "success": False,
            "error": f"Unknown device type '{device_type}'. Supported: {list(config_commands.keys())}",
        }

    result = await ssh_execute(
        host=host,
        username=username,
        command=command,
        port=port,
        password=password,
        key_path=key_path,
    )
    result["device_type"] = device_type
    return result


async def snmp_get(
    host: str,
    oid: str,
    community: str = "public",
    port: int = 161,
) -> dict:
    """Perform an SNMP GET using the snmpget command-line tool.

    Args:
        host: Hostname or IP of the device.
        oid: SNMP OID to query (e.g., '1.3.6.1.2.1.1.1.0' for sysDescr).
        community: SNMP community string.
        port: SNMP port.

    Returns:
        Dict with the SNMP response.
    """
    cmd = [
        "snmpget", "-v2c",
        "-c", community,
        f"{host}:{port}",
        oid,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    return {
        "host": host,
        "oid": oid,
        "success": proc.returncode == 0,
        "output": stdout.decode().strip(),
        "error": stderr.decode().strip() or None,
    }


async def snmp_walk(
    host: str,
    oid: str,
    community: str = "public",
    port: int = 161,
) -> dict:
    """Perform an SNMP WALK using the snmpwalk command-line tool.

    Args:
        host: Hostname or IP of the device.
        oid: Base OID to walk.
        community: SNMP community string.
        port: SNMP port.

    Returns:
        Dict with the SNMP walk results.
    """
    cmd = [
        "snmpwalk", "-v2c",
        "-c", community,
        f"{host}:{port}",
        oid,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    output = stdout.decode().strip()
    entries = [line for line in output.splitlines() if line.strip()] if output else []

    return {
        "host": host,
        "oid": oid,
        "success": proc.returncode == 0,
        "entry_count": len(entries),
        "entries": entries,
        "error": stderr.decode().strip() or None,
    }
