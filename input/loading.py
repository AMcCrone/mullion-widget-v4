# input/loading.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LoadKind(str, Enum):
    WIND = "wind"
    BARRIER = "barrier"
    DEAD = "dead"  # e.g., glazing weight, location-specific


@dataclass
class Load:
    """
    Single load item.

    Units / conventions:
      - magnitude: if distribution == "uniform" -> N/mm (force per mm of mullion length).
                   if distribution == "point" -> N (single concentrated force).
      - For barrier loads we also allow 'height_mm' to be provided where relevant.
    """
    kind: LoadKind
    magnitude: float
    distribution: str = "uniform"  # "uniform" or "point"
    height_mm: Optional[float] = None  # for barrier, or where height matters (mm)

    def __post_init__(self):
        if self.magnitude < 0:
            raise ValueError("magnitude must be non-negative.")
        if self.distribution not in ("uniform", "point"):
            raise ValueError("distribution must be 'uniform' or 'point'.")
        if self.kind == LoadKind.BARRIER and (self.height_mm is None or self.height_mm <= 0):
            raise ValueError("Barrier loads must supply a positive height_mm (mm).")

    def magnitude_n_per_m(self) -> Optional[float]:
        """Convert a uniform magnitude in N/mm to N/m (useful for beam formulas).
        Returns None for point loads."""
        if self.distribution != "uniform":
            return None
        return self.magnitude * 1000.0  # N/mm -> N/m

    def magnitude_n(self) -> Optional[float]:
        """Return magnitude as N (for point loads). For uniform loads returns None."""
        if self.distribution == "point":
            return self.magnitude
        return None


@dataclass
class LoadCase:
    """Group of loads that belong to the same case (e.g., ULS wind + dead)."""
    name: str
    loads: list[Load]
    case_type: str = "ULS"  # ULS or SLS

    def total_uniform_n_per_m(self) -> float:
        """Sum of uniform loads (converted to N/m)."""
        total = 0.0
        for ld in self.loads:
            if ld.distribution == "uniform":
                total += ld.magnitude * 1000.0  # N/mm -> N/m
        return total

    def total_point_n(self) -> float:
        """Sum of point loads (N)."""
        total = 0.0
        for ld in self.loads:
            if ld.distribution == "point":
                total += ld.magnitude
        return total


# Streamlit UI helper

def loading_ui(container=None, key_prefix: str = "load",
               default_wind_n_per_mm: float = 0.05,
               default_barrier_n_per_mm: float = 0.1,
               default_barrier_height_mm: float = 1100.0) -> "LoadCase":
    """
    Render load inputs on the main page and return a LoadCase.

    Notes:
    - Uniform loads are entered in N/mm (force per mm of mullion length).
    - Point loads may be added (N).
    - container: optional Streamlit container
    - key_prefix: unique widget key prefix
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("loading_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    with parent.expander("Loads", expanded=False):
        parent.markdown("**Enter loads** (units: mm / N). Uniform loads = N/mm (force per mm of mullion length).")

        # toggles for basic loads
        wind_enabled = parent.checkbox("Include wind load", value=True, key=f"{key_prefix}_wind_en")
        barrier_enabled = parent.checkbox("Include barrier load", value=False, key=f"{key_prefix}_bar_en")
        dead_enabled = parent.checkbox("Include dead load", value=False, key=f"{key_prefix}_dead_en")

        loads = []

        if wind_enabled:
            wind_val = parent.number_input(
                "Wind load (N/mm, uniform)",
                min_value=0.0,
                value=float(default_wind_n_per_mm),
                format="%.6f",
                key=f"{key_prefix}_wind_val"
            )
            loads.append(Load(kind=LoadKind.WIND, magnitude=wind_val, distribution="uniform"))

        if barrier_enabled:
            barrier_val = parent.number_input(
                "Barrier load (N/mm, uniform)",
                min_value=0.0,
                value=float(default_barrier_n_per_mm),
                format="%.6f",
                key=f"{key_prefix}_bar_val"
            )
            barrier_height = parent.number_input(
                "Barrier load height (mm)",
                min_value=1.0,
                value=float(default_barrier_height_mm),
                format="%.1f",
                key=f"{key_prefix}_bar_height"
            )
            loads.append(Load(kind=LoadKind.BARRIER, magnitude=barrier_val, distribution="uniform", height_mm=barrier_height))

        if dead_enabled:
            dead_val = parent.number_input(
                "Dead load (N/mm, uniform)",
                min_value=0.0,
                value=0.0,
                format="%.6f",
                key=f"{key_prefix}_dead_val"
            )
            loads.append(Load(kind=LoadKind.DEAD, magnitude=dead_val, distribution="uniform"))

        # Optionally allow one point load (extendable later to multiple)
        add_point = parent.checkbox("Add a concentrated point load (N)", value=False, key=f"{key_prefix}_pt_en")
        if add_point:
            pt_val = parent.number_input(
                "Point load magnitude (N)",
                min_value=0.0,
                value=0.0,
                format="%.1f",
                key=f"{key_prefix}_pt_val"
            )
            loads.append(Load(kind=LoadKind.DEAD, magnitude=pt_val, distribution="point"))

        case_name = parent.text_input("Load case name", value="ULS_wind_barrier", key=f"{key_prefix}_case_name")
        case_type = parent.selectbox("Load case type", ["ULS", "SLS"], index=0, key=f"{key_prefix}_case_type")

        lc = LoadCase(name=case_name, loads=loads, case_type=case_type)

        parent.markdown("**Summary**")
        parent.write(f"Total uniform load (N/m): {lc.total_uniform_n_per_m():.1f}")
        parent.write(f"Total point load (N): {lc.total_point_n():.1f}")

    return lc

