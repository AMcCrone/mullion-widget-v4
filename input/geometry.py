# input/geometry.py
from dataclasses import dataclass


@dataclass
class Geometry:
    """Simple geometry for a mullion bay.

    Units:
      - span_mm: span between supports in mm (length along mullion that carries bending)
      - bay_width_mm: width of the glazing bay / tributary width in mm
    """
    span_mm: float
    bay_width_mm: float

    def __post_init__(self):
        if self.span_mm <= 0:
            raise ValueError("span_mm must be > 0 (mm).")
        if self.bay_width_mm <= 0:
            raise ValueError("bay_width_mm must be > 0 (mm).")

    @property
    def span_m(self) -> float:
        """Span in metres."""
        return self.span_mm / 1000.0

    @property
    def bay_width_m(self) -> float:
        """Bay width in metres."""
        return self.bay_width_mm / 1000.0

    @property
    def tributary_area_m2(self) -> float:
        """Simple tributary area in m^2 (span * bay width)."""
        return self.span_m * self.bay_width_m

    def as_dict(self):
        return {
            "span_mm": self.span_mm,
            "bay_width_mm": self.bay_width_mm,
            "span_m": self.span_m,
            "bay_width_m": self.bay_width_m,
            "tributary_area_m2": self.tributary_area_m2,
        }



def geometry_ui(container=None, key_prefix: str = "geom",
                default_span_mm: float = 3000.0, default_bay_width_mm: float = 1000.0) -> "Geometry":
    """
    Render geometry inputs on the main page (not sidebar) and return a Geometry instance.

    Parameters
    - container: Streamlit container to render into (defaults to streamlit module)
    - key_prefix: unique prefix for widget keys to avoid collisions
    - default_span_mm/default_bay_width_mm: initial values

    Usage:
        geom = geometry_ui(st, key_prefix="main_geom")
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("geometry_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    with parent.expander("Geometry", expanded=True):
        span_mm = parent.number_input(
            "Span (mm)",
            min_value=1.0,
            value=float(default_span_mm),
            format="%.1f",
            key=f"{key_prefix}_span_mm"
        )
        bay_width_mm = parent.number_input(
            "Bay width (mm)",
            min_value=1.0,
            value=float(default_bay_width_mm),
            format="%.1f",
            key=f"{key_prefix}_bay_width_mm"
        )

        # quick readout
        geom = Geometry(span_mm=span_mm, bay_width_mm=bay_width_mm)
        parent.write(f"Tributary area: **{geom.tributary_area_m2:.4f} m²**")

    return geom

