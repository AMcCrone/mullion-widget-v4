# input/geometry.py
from dataclasses import dataclass

@dataclass
class Geometry:
    """Simple geometry for a mullion bay.

    Units:
      - span_mm: span between supports in mm
      - bay_width_mm: bay width in mm
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
        return self.span_mm / 1000.0

    @property
    def bay_width_m(self) -> float:
        return self.bay_width_mm / 1000.0

    @property
    def tributary_area_m2(self) -> float:
        return self.span_m * self.bay_width_m

    def as_dict(self):
        return {
            "span_mm": self.span_mm,
            "bay_width_mm": self.bay_width_mm,
            "span_m": self.span_m,
            "bay_width_m": self.bay_width_m,
            "tributary_area_m2": self.tributary_area_m2,
        }


# ---------- UI helper (always visible inputs) ----------
def geometry_ui(container=None, key_prefix: str = "geom",
                default_span_mm: float = 3000.0, default_bay_width_mm: float = 1000.0) -> Geometry:
    """
    Render geometry inputs as always-visible fields (no expander) and return a Geometry instance.

    Parameters:
        - container: Streamlit container (default: `st`)
        - key_prefix: unique widget key prefix
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("geometry_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    # Ensure session_state.inputs dictionary exists
    if "inputs" not in st.session_state:
        st.session_state.inputs = {}

    # defaults read from session_state or fallback defaults
    def _get_default(name, fallback):
        return st.session_state.inputs.get(name, fallback)

    # Layout: two columns (similar to your example)
    col1, col2 = parent.columns(2)

    with col1:
        span_mm = parent.number_input(
            "Span (mm)",
            min_value=1.0,
            value=float(_get_default(f"{key_prefix}_span_mm", default_span_mm)),
            format="%.1f",
            key=f"{key_prefix}_span_mm_widget"
        )
        # save into session_state so other modules/forms can read
        st.session_state.inputs[f"{key_prefix}_span_mm"] = span_mm

    with col2:
        bay_width_mm = parent.number_input(
            "Bay width (mm)",
            min_value=1.0,
            value=float(_get_default(f"{key_prefix}_bay_width_mm", default_bay_width_mm)),
            format="%.1f",
            key=f"{key_prefix}_bay_width_mm_widget"
        )
        st.session_state.inputs[f"{key_prefix}_bay_width_mm"] = bay_width_mm
        
    # Display read-only computed values
    geom = Geometry(span_mm=span_mm, bay_width_mm=bay_width_mm)

    return geom
