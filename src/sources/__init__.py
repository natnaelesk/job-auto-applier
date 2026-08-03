"""Foreign job portal sources (freehire, LinkedIn guest)."""

from sources.base import JobSource
from sources.freehire import FreehireSource
from sources.linkedin import LinkedInSource

__all__ = ["JobSource", "FreehireSource", "LinkedInSource"]
