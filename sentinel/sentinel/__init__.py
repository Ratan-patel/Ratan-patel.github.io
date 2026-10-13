"""Sentinel - a model-agnostic, read-only security assessment agent.

Sentinel runs any model behind any API (including a private, self-hosted
OpenAI-compatible gateway) and gives it a fixed set of read-only assessment
tools. Every tool re-checks authorization through a guard that no prompt and no
scope file can override for protected target classes.

It cannot attack anything. It has no exploitation, brute-force, credential,
payload, persistence or denial-of-service capability, and by design it will not
be given any.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
