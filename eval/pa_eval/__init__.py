"""Evaluation harness for the Proveedor Abierto case: judges the engine's output, never feeds the engine."""

from pathlib import Path

REFERENCES = Path(__file__).resolve().parents[1] / "references"
