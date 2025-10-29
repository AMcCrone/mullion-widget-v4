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
    magnitude: float  # N/mm for uniform, N for point
    distribution: str = "uniform"  # "uniform" or "point"
    height_mm: Optional[float] = None

    def __post_init__(self):
        if self.magnitude < 0:
            raise ValueError("magnitude must be non-negative.")
        if self.distribution not in ("uniform", "point"):
            raise ValueError("distribution must be 'uniform' or 'point'.")
        if self.kind == LoadKind.BARRIER and self.distribution == "uniform" and (self.height_mm is None or self.height_mm <= 0):
            raise ValueError("Barrier loads must provide positive height_mm (mm).")

    def magnitude_n_per_m(self) -> Optional[float]:
        """Convert to N/m for display purposes"""
        if self.distribution != "uniform":
            return None
        return self.magnitude * 1000.0

    def magnitude_n(self) -> Optional[float]:
        """Return point load magnitude in N"""
        if self.distribution == "point":
            return self.magnitude
        return None


@dataclass
class LoadingInputs:
    """Container for loading input values from UI"""
    # Wind load
    include_wind: bool = True
    wind_pressure_kpa: float = 1.0
    bay_width_mm: float = 3000.0
    
    # Barrier load
    include_barrier: bool = False
    barrier_load_kn_per_m: float = 0.74
    barrier_height_mm: float = 1100.0
    
    def wind_load_n_per_mm(self) -> float:
        """
        Convert wind pressure to uniform load on mullion
        
        Wind pressure (kPa) × Bay width (mm) × 10^-3 = N/mm
        """
        if not self.include_wind:
            return 0.0
        return self.wind_pressure_kpa * self.bay_width_mm * 1e-3
    
    def barrier_load_n_per_mm(self) -> float:
        """
        Convert barrier load to N/mm
        
        Barrier load (kN/m) = N/mm (no conversion needed)
        """
        if not self.include_barrier:
            return 0.0
        return self.barrier_load_kn_per_m
    
    def to_loads(self) -> List[Load]:
        """Convert input values to Load objects"""
        loads = []
        
        if self.include_wind:
            loads.append(Load(
                kind=LoadKind.WIND,
                magnitude=self.wind_load_n_per_mm(),
                distribution="uniform"
            ))
        
        if self.include_barrier:
            loads.append(Load(
                kind=LoadKind.BARRIER,
                magnitude=self.barrier_load_n_per_mm(),
                distribution="uniform",
                height_mm=self.barrier_height_mm
            ))
        
        return loads


def loading_ui(container=None, key_prefix: str = "load",
               bay_width_mm: float = 3000.0) -> LoadingInputs:
    """
    Render loading inputs in Streamlit UI.
    
    Parameters
    ----------
    container : streamlit container, optional
        Container to render UI in (if None, uses st directly)
    key_prefix : str
        Prefix for session state keys
    bay_width_mm : float
        Bay width from geometry section (mm)
        
    Returns
    -------
    LoadingInputs
        Container with all loading input values
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

    # Layout: two columns for better organization
    col1, col2 = parent.columns(2)

    # ========== WIND LOAD ==========
    with col1:
        parent.markdown("#### Wind Load")
        
        include_wind = parent.checkbox(
            "Include wind load",
            value=bool(_get_default(f"{key_prefix}_wind_en", True)),
            key=f"{key_prefix}_wind_en_widget",
            help="Check to include wind pressure loading on the mullion"
        )
        st.session_state.inputs[f"{key_prefix}_wind_en"] = include_wind
        
        wind_pressure_kpa = parent.number_input(
            "Wind pressure (kPa)",
            min_value=0.0,
            max_value=10.0,
            value=float(_get_default(f"{key_prefix}_wind_kpa", 1.0)),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_wind_kpa_widget",
            help="Design wind pressure acting on the facade",
            disabled=not include_wind
        )
        st.session_state.inputs[f"{key_prefix}_wind_kpa"] = wind_pressure_kpa

    # ========== BARRIER LOAD ==========
    with col2:
        parent.markdown("#### Barrier Load")
        
        include_barrier = parent.checkbox(
            "Include barrier load",
            value=bool(_get_default(f"{key_prefix}_barrier_en", False)),
            key=f"{key_prefix}_barrier_en_widget",
            help="Check to include horizontal line load from barrier"
        )
        st.session_state.inputs[f"{key_prefix}_barrier_en"] = include_barrier
        
        barrier_load_kn_per_m = parent.number_input(
            "Barrier load (kN/m)",
            min_value=0.0,
            max_value=5.0,
            value=float(_get_default(f"{key_prefix}_barrier_knm", 0.74)),
            step=0.01,
            format="%.2f",
            key=f"{key_prefix}_barrier_knm_widget",
            help="Horizontal line load from barrier",
            disabled=not include_barrier
        )
        st.session_state.inputs[f"{key_prefix}_barrier_knm"] = barrier_load_kn_per_m
        
        barrier_height_mm = parent.number_input(
            "Barrier height (mm)",
            min_value=0.0,
            max_value=2000.0,
            value=float(_get_default(f"{key_prefix}_barrier_height", 1100.0)),
            step=50.0,
            format="%.0f",
            key=f"{key_prefix}_barrier_height_widget",
            help="Height above mullion base where barrier load acts",
            disabled=not include_barrier
        )
        st.session_state.inputs[f"{key_prefix}_barrier_height"] = barrier_height_mm

    # Create LoadingInputs object
    loading_inputs = LoadingInputs(
        include_wind=include_wind,
        wind_pressure_kpa=wind_pressure_kpa,
        bay_width_mm=bay_width_mm,
        include_barrier=include_barrier,
        barrier_load_kn_per_m=barrier_load_kn_per_m,
        barrier_height_mm=barrier_height_mm
    )
    
    # Display summary in columns
    sum_col1, sum_col2, sum_col3 = parent.columns(3)
    
    with sum_col1:
        parent.metric(
            "Wind Load",
            f"{loading_inputs.wind_load_n_per_mm():.2f} N/mm" if include_wind else "Not included",
            help="Uniform distributed load from wind"
        )
    
    with sum_col2:
        parent.metric(
            "Barrier Load",
            f"{loading_inputs.barrier_load_n_per_mm():.2f} N/mm" if include_barrier else "Not included",
            help="Line load from barrier/balustrade"
        )
    
    with sum_col3:
        if include_barrier:
            parent.metric(
                "Barrier Height",
                f"{barrier_height_mm:.0f} mm",
                help="Height of barrier load application"
            )
        else:
            parent.metric("Barrier Height", "N/A")

    return loading_inputs


# For backwards compatibility with existing code
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
