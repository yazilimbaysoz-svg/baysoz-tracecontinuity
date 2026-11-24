"""Baysöz Labs <baysozlabs@proton.me> — offline distributed-trace continuity oracle."""

from .audit import audit_document, audit_trace_document
from .model import InputError, TraceDocument, parse_document
from .policy import Policy
from .report import AuditReport

__version__ = "1.0.0"
ATTRIBUTION = "Baysöz Labs <baysozlabs@proton.me>"
PROJECT = "baysoz-tracecontinuity"
POLICY_DEFAULTS = Policy()

__all__ = [
    "ATTRIBUTION",
    "AuditReport",
    "InputError",
    "POLICY_DEFAULTS",
    "Policy",
    "PROJECT",
    "TraceDocument",
    "audit_document",
    "audit_trace_document",
    "parse_document",
    "__version__",
]
