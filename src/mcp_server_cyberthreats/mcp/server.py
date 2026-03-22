"""FastMCP threat-intelligence server for the CyberThreats Architecture Security Reviewer.

This module implements a Model Context Protocol (MCP) server that exposes
live CISA Known Exploited Vulnerabilities (KEV) data as MCP primitives
(tools, resources, and prompts) consumed by the Streamlit application via
``fetch_mcp_context`` in ``app/ui.py``.

The server is launched as a stdio child process using ``PythonStdioTransport``.
It is **not** intended to be run as a long-lived network service — a fresh
process is spawned per request session.

MCP primitives exposed
----------------------
Tools:
    get_live_cisa_threats(limit)  — cloud-relevant KEV entries as Markdown
    get_cisa_feed_metadata()      — source URL, fetch timestamp, keyword list

Resources:
    intel://cisa/cloud-keywords   — static keyword list used for filtering
    intel://cisa/feed-info        — human-readable feed source description

Prompts:
    audit_prompt  — security-audit prompt template
"""
import json
import os
from datetime import datetime, timezone

import requests
from fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

CLOUD_KEYWORDS = [
    "cloud",
    "aws",
    "azure",
    "container",
    "kubernetes",
    "s3",
    "docker",
    "serverless",
    "iam",
]


# ---------------------------------------------------------------------------
# Threat intelligence service
# ---------------------------------------------------------------------------

class CisaKevThreatIntelService:
    """Service layer for fetching and filtering CISA KEV data.

    Retrieves the public CISA Known Exploited Vulnerabilities JSON feed and
    filters entries to those relevant to cloud and container environments
    using a keyword list defined in ``CLOUD_KEYWORDS``.
    """

    def fetch_feed(self) -> dict:
        """Fetch the raw CISA KEV JSON feed.

        Returns:
            Parsed JSON payload from the CISA feed endpoint.

        Raises:
            requests.HTTPError: If the HTTP request returns an error status.
        """
        timeout = int(os.environ.get("CISA_FEED_TIMEOUT", "10"))
        response = requests.get(FEED_URL, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def get_cloud_threat_entries(self, limit: int) -> list[str]:
        """Return up to *limit* cloud-relevant CVE entries as Markdown strings.

        Vulnerabilities are sorted by ``dateAdded`` (most recent first) and
        filtered to those whose name or description contains at least one of
        the ``CLOUD_KEYWORDS`` tokens.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of Markdown-formatted bullet strings, each describing one CVE.
        """
        data = self.fetch_feed()
        threats: list[str] = []
        vulnerabilities = data.get("vulnerabilities", [])
        sorted_vulns = sorted(vulnerabilities, key=lambda item: item.get("dateAdded", ""), reverse=True)

        for vuln in sorted_vulns:
            description = vuln.get("shortDescription", "")
            name = vuln.get("vulnerabilityName", "")
            description_lower = description.lower()
            name_lower = name.lower()

            if any(keyword in description_lower or keyword in name_lower for keyword in CLOUD_KEYWORDS):
                entry = (
                    f"- **{vuln.get('cveID', 'Unknown CVE')} ({name})**: "
                    f"{description} (Added: {vuln.get('dateAdded', 'N/A')})"
                )
                threats.append(entry)

            if len(threats) >= limit:
                break

        return threats

    def get_live_cisa_threats_markdown(self, limit: int = 8) -> str:
        """Return cloud-relevant KEV entries as a Markdown bullet list.

        Args:
            limit: Maximum number of CVEs to include.

        Returns:
            Newline-joined Markdown bullet strings, or a fallback message if
            no matching entries are found.
        """
        threats = self.get_cloud_threat_entries(limit=limit)
        if not threats:
            return "No recent cloud-specific CVEs found in CISA KEV."
        return "\n".join(threats)

    def get_feed_metadata_json(self) -> str:
        """Return source and fetch-time metadata for the CISA KEV feed as JSON.

        Returns:
            Pretty-printed JSON string with ``source``, ``url``,
            ``fetchedAtUtc``, and ``cloudKeywords`` fields.
        """
        payload = {
            "source": "CISA KEV",
            "url": FEED_URL,
            "fetchedAtUtc": datetime.now(timezone.utc).isoformat(),
            "cloudKeywords": CLOUD_KEYWORDS,
        }
        return json.dumps(payload, indent=2)

    def get_cloud_keywords_markdown(self) -> str:
        """Return the cloud-filter keyword list as a Markdown bullet list.

        Returns:
            Newline-joined Markdown bullet strings for each keyword.
        """
        return "\n".join(f"- {keyword}" for keyword in CLOUD_KEYWORDS)

    def get_feed_info_text(self) -> str:
        """Return a human-readable description of the CISA KEV feed source.

        Returns:
            Multi-line plain-text string with feed name, URL, and scope.
        """
        return (
            "CISA Known Exploited Vulnerabilities (KEV) Feed\n"
            f"Source URL: {FEED_URL}\n"
            "Scope: Public catalog of CVEs with evidence of active exploitation."
        )


# ---------------------------------------------------------------------------
# MCP server setup
# ---------------------------------------------------------------------------

def create_mcp_server() -> FastMCP:
    """Build and return a configured ``FastMCP`` server instance.

    Registers all tools, resources, and prompts against the
    ``CloudThreatIntel`` MCP server name and returns the server object
    ready to be run with ``server.run(transport='stdio')``.

    Returns:
        A ``FastMCP`` instance with the following primitives registered:

        **Tools**:
            - ``get_live_cisa_threats`` — cloud-relevant KEV bullet list
            - ``get_cisa_feed_metadata`` — feed source and timestamp JSON

        **Resources**:
            - ``intel://cisa/cloud-keywords`` — keyword filter list
            - ``intel://cisa/feed-info`` — feed source description

        **Prompts**:
            - ``audit_prompt`` — pre-populated audit prompt
    """
    mcp = FastMCP("CloudThreatIntel")
    threat_service = CisaKevThreatIntelService()

    _default_limit = int(os.environ.get("CISA_THREAT_LIMIT", "8"))

    @mcp.tool()
    def get_live_cisa_threats(limit: int = _default_limit) -> str:
        """Fetches latest cloud-relevant vulnerabilities from CISA KEV as Markdown bullet points."""
        try:
            return threat_service.get_live_cisa_threats_markdown(limit=limit)
        except Exception as exc:
            return f"Error fetching CISA data: {exc}"

    @mcp.tool()
    def get_cisa_feed_metadata() -> str:
        """Returns source and timestamp metadata for the CISA KEV feed."""
        return threat_service.get_feed_metadata_json()

    @mcp.resource("intel://cisa/cloud-keywords")
    def cisa_cloud_keywords_resource() -> str:
        """Static cloud keyword list used to filter KEV data."""
        return threat_service.get_cloud_keywords_markdown()

    @mcp.resource("intel://cisa/feed-info")
    def cisa_feed_info_resource() -> str:
        """Static details about the CISA KEV feed source."""
        return threat_service.get_feed_info_text()

    @mcp.prompt()
    def audit_prompt(threat_intel: str, architecture_context: str = "cloud architecture diagram") -> str:
        """Generates the canonical auditor prompt used by the vision model."""
        return f"""
            Act as a Principal Cloud Security Architect.

            LIVE THREAT INTEL FROM CISA:
            {threat_intel}

            TARGET CONTEXT:
            {architecture_context}

            TASK 1:
            1. Identify components in this cloud diagram.
            2. Audit the architecture against the CISA threats provided.
            3. Identify 2 critical vulnerabilities.
            4. Provide production-ready Terraform code to remediate these issues. it is very important that the code is production-ready and secure. Do not provide any explanation, only provide the code. 
            5. If the diagram is missing any components, make reasonable assumptions and add them to the code. Do not provide any explanation, only provide the code.
            6. Ensure the code is formatted correctly and follows best practices for security and maintainability.
            7. Ensure the code is idempotent and can be applied multiple times without causing errors or unintended side effects.
            8. Ensure the code is compatible with the latest version of Terraform and any relevant providers.
            
            TASK 2:
            1. Attempt to create complete Terraform code for the entire architecture diagram, including any missing components. it is very important that the code is production-ready and secure. Do not provide any explanation, only provide the code.


            Format in clean Markdown. No conversational filler.

            """.strip()

    return mcp


def run_mcp_server() -> None:
    """Create the MCP server and start it on stdio transport.

    Entry point for both direct execution and ``PythonStdioTransport``.
    Used by VSCode and Claude Code Desktop via stdio MCP config.
    Communicates exclusively over stdin/stdout using the MCP protocol
    and exits when the client closes the connection.
    """
    server = create_mcp_server()
    server.run(transport="stdio")


def run_mcp_server_http() -> None:
    """Create the MCP server and start it on HTTP (streamable-http) transport.

    Binds to ``MCP_HTTP_HOST:MCP_HTTP_PORT`` (defaults: ``localhost:8000``).
    The MCP endpoint is available at ``http://<host>:<port>/mcp``.
    Used by the Streamlit app when ``MCP_SERVER_URL`` is set in the environment.
    """
    host = os.environ.get("MCP_HTTP_HOST", "localhost")
    port = int(os.environ.get("MCP_HTTP_PORT", "8000"))
    server = create_mcp_server()
    server.run(transport="streamable-http", host=host, port=port)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_mcp_server()
