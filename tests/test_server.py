"""Basic tests for the Network MCP Server."""

import shutil

import pytest

from network_mcp.diagnostics import dns_lookup, port_scan
from network_mcp.monitoring import check_host

has_ping = shutil.which("ping") is not None


@pytest.mark.asyncio
async def test_dns_lookup_structure():
    """dns_lookup should return a well-formed result dict."""
    # Use a public DNS server to avoid local resolver issues
    result = await dns_lookup("localhost", "A", server="8.8.8.8")
    assert "name" in result
    assert "record_type" in result
    assert result["record_type"] == "A"


@pytest.mark.asyncio
async def test_port_scan_returns_structure():
    """Port scan should return a well-structured result."""
    result = await port_scan("127.0.0.1", ports=[80, 443], timeout=0.5)
    assert "host" in result
    assert result["host"] == "127.0.0.1"
    assert "total_scanned" in result
    assert result["total_scanned"] == 2
    assert "open_ports" in result
    assert "closed_ports" in result


@pytest.mark.asyncio
@pytest.mark.skipif(not has_ping, reason="ping not available")
async def test_check_host_localhost():
    """Checking localhost should succeed."""
    result = await check_host("127.0.0.1", timeout=2.0)
    assert result["host"] == "127.0.0.1"
    assert "reachable" in result


def test_server_imports():
    """The MCP server should import without errors."""
    from network_mcp.server import mcp

    tools = mcp._tool_manager._tools
    assert len(tools) == 15


def test_server_has_all_tool_categories():
    """Server should have tools from all three categories."""
    from network_mcp.server import mcp

    tool_names = list(mcp._tool_manager._tools.keys())

    # Diagnostics
    assert "tool_ping" in tool_names
    assert "tool_dns_lookup" in tool_names

    # Monitoring
    assert "tool_check_host" in tool_names
    assert "tool_check_http" in tool_names

    # Device management
    assert "tool_ssh_execute" in tool_names
    assert "tool_snmp_get" in tool_names
