# input/loading.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class LoadKind(str, Enum):
    WIND = "wind"
    BARRIER = "barrier"
    DEAD = "dead"


@dataclass
class Load:
    """
    magnitude: if distribution == 'uniform' -> N/mm (force per mm of mullion length)
               if distribution == 'point' -> N
    """
    kind: LoadKind
    magnitude: float
    distribution: str = "uniform"  # "uniform" or "point"
    height_mm: Optional[float] = None

    def __post_init__(self):
        if self.magnitude < 0:
            raise ValueError("magnitude must be non-negative.")
        if self.distribution not in ("uniform", "point"):
            raise ValueError("distribution must be 'uniform' or 'point'.")
        if self.kind == LoadKind.BARRIER and (self.height_mm is None or self.height_mm <= 0):
            raise ValueError("Barrier loads must provide positive height_mm (mm).")

    def magnitude_n_per_m(self) -> Optional[float]:
        if self.distribution != "uniform":
            return None
        return self.magnitude * 1000.0

    def magnitude_n(self) -> Optional[float]:
        if self.distribution == "point":
            return self.magnitude
        return None


@dataclass
class LoadCase:
    name: str
    loads: List[Load]
    case_type: str = "ULS"

    def total_uniform_n_per_m(self) -> float:
        total = 0.0
        for ld in self.loads:
            if ld.distribution == "uniform":
                total += ld.magnitude * 1000.0
        return total

    def total_point_n(self) -> float:
        total = 0.0
        for ld in self.loads:
            if ld.distribution == "point":
                total += ld.magnitude
        return total


# ---------- UI helper (always-visible inputs) ----------
def loading_ui(container=None, key_prefix: str = "load",
               default_wind_n_per_mm: float = 0.05,
               default_barrier_n_per_mm: float = 0.1,
               default_barrier_height_mm: float = 1100.0) -> LoadCase:
    """
    Render load inputs as visible fields (no expander). Returns a LoadCase dataclass.

    Uses st.session_state.inputs[...] for defaults and persistence.
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("loading_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    if "inputs" not in st.session_state:
        st.session_state.inputs = {}

    def _get_default(name, fallback):
        return st.session_state.inputs.get(name, fallback)

    # Layout: two columns
    col1, col2 = parent.columns(2)

    with col1:
        parent.write("**Loads (uniform loads = N/mm)**")
        wind_enabled = parent.checkbox("Include wind load", value=bool(_get_default(f"{key_prefix}_wind_en", True)), key=f"{key_prefix}_wind_en_widget")
        wind_val = parent.number_input("Wind load (N/mm)", min_value=0.0, value=float(_get_default(f"{key_prefix}_wind_val", default_wind_n_per_mm)), format="%.6f", key=f"{key_prefix}_wind_val_widget")
        st.session_state.inputs[f"{key_prefix}_wind_en"] = wind_enabled
        st.session_state.inputs[f"{key_prefix}_wind_val"] = wind_val

        barrier_enabled = parent.checkbox("Include barrier load", value=bool(_get_default(f"{key_prefix}_bar_en", False)), key=f"{key_prefix}_bar_en_widget")
        barrier_val = parent.number_input("Barrier load (N/mm)", min_value=0.0, value=float(_get_default(f"{key_prefix}_bar_val", default_barrier_n_per_mm)), format="%.6f", key=f"{key_prefix}_bar_val_widget")
        barrier_height = parent.number_input("Barrier load height (mm)", min_value=1.0, value=float(_get_default(f"{key_prefix}_bar_height", default_barrier_height_mm)), format="%.1f", key=f"{key_prefix}_bar_height_widget")
        st.session_state.inputs[f"{key_prefix}_bar_en"] = barrier_enabled
        st.session_state.inputs[f"{key_prefix}_bar_val"] = barrier_val
        st.session_state.inputs[f"{key_prefix}_bar_height"] = barrier_height

        dead_enabled = parent.checkbox("Include dead load", value=bool(_get_default(f"{key_prefix}_dead_en", False)), key=f"{key_prefix}_dead_en_widget")
        dead_val = parent.number_input("Dead load (N/mm)", min_value=0.0, value=float(_get_default(f"{key_prefix}_dead_val", 0.0)), format="%.6f", key=f"{key_prefix}_dead_val_widget")
        st.session_state.inputs[f"{key_prefix}_dead_en"] = dead_enabled
        st.session_state.inputs[f"{key_prefix}_dead_val"] = dead_val

    with col2:
        parent.write("**Optional concentrated load**")
        add_point = parent.checkbox("Add concentrated point load (N)", value=bool(_get_default(f"{key_prefix}_pt_en", False)), key=f"{key_prefix}_pt_en_widget")
        pt_val = parent.number_input("Point load magnitude (N)", min_value=0.0, value=float(_get_default(f"{key_prefix}_pt_val", 0.0)), format="%.1f", key=f"{key_prefix}_pt_val_widget")
        st.session_state.inputs[f"{key_prefix}_pt_en"] = add_point
        st.session_state.inputs[f"{key_prefix}_pt_val"] = pt_val

        case_name = parent.text_input("Load case name", value=_get_default(f"{key_prefix}_case_name", "ULS_wind_barrier"), key=f"{key_prefix}_case_name_widget")
        case_type = parent.selectbox("Load case type", options=["ULS", "SLS"], index=0 if _get_default(f"{key_prefix}_case_type", "ULS") == "ULS" else 1, key=f"{key_prefix}_case_type_widget")
        st.session_state.inputs[f"{key_prefix}_case_name"] = case_name
        st.session_state.inputs[f"{key_prefix}_case_type"] = case_type

        # summary
        # compute totals temporarily
        loads = []
        if wind_enabled:
            loads.append(Load(kind=LoadKind.WIND, magnitude=wind_val, distribution="uniform"))
        if barrier_enabled:
            loads.append(Load(kind=LoadKind.BARRIER, magnitude=barrier_val, distribution="uniform", height_mm=barrier_height))
        if dead_enabled:
            loads.append(Load(kind=LoadKind.DEAD, magnitude=dead_val, distribution="uniform"))
        if add_point and pt_val > 0:
            loads.append(Load(kind=LoadKind.DEAD, magnitude=pt_val, distribution="point"))

        lc = LoadCase(name=case_name, loads=loads, case_type=case_type)
        parent.write("**Load summary**")
        parent.write(f"- Total uniform load (N/m): {lc.total_uniform_n_per_m():.1f}")
        parent.write(f"- Total point load (N): {lc.total_point_n():.1f}")

    return lc
