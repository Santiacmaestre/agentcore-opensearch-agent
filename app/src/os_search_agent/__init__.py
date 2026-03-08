"""os_search_agent -- OpenSearch data exploration agent powered by Strands + MCP."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("os-search-agent")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = ["__version__"]
