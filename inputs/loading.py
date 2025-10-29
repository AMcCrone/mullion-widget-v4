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
    barrier_load_kn: float = 0.74  # Point load in kN
    barrier_height_mm: float = 1100.0
    
    def wind_load_n_per_mm(self) -> float:
        """
        Convert wind pressure to uniform load on mullion
        
        Wind pressure (kPa) × Bay width (mm) × 10^-3 = N/mm
        """
        if not self.include_wind:
            return 0.0
        return self.wind_pressure_kpa * self.bay_width_mm * 1e-3
    
    def barrier_load_n(self) -> float:
        """
        Convert barrier load to N (point load on mullion)
        
        Barrier load (kN) × 1000 = N
        """
        if not self.include_barrier:
            return 0.0
        return self.barrier_load_kn * 1000.0
    
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
            # Barrier is a point load, not distributed
            loads.append(Load(
                kind=LoadKind.BARRIER,
                magnitude=self.barrier_load_n(),
                distribution="point",
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
        
        if include_wind:
            # Calculate and display derived values
            wind_n_per_mm = wind_pressure_kpa * bay_width_mm * 1e-3
            wind_n_per_m = wind_n_per_mm * 1000.0

    # ========== BARRIER LOAD ==========
    with col2:
        parent.markdown("#### Barrier/Balustrade Load")
        
        include_barrier = parent.checkbox(
            "Include barrier load",
            value=bool(_get_default(f"{key_prefix}_barrier_en", False)),
            key=f"{key_prefix}_barrier_en_widget",
            help="Check to include horizontal line load from barrier/balustrade"
        )
        st.session_state.inputs[f"{key_prefix}_barrier_en"] = include_barrier
        
        barrier_load_kn_per_m = parent.number_input(
            "Barrier load (kN/m)",
            min_value=0.0,
            max_value=5.0,
            value=float(_get_default(f"{key_prefix}_barrier_knm", 0.74)),
            step=0.01,
            format="%.3f",
            key=f"{key_prefix}_barrier_knm_widget",
            help="Horizontal line load from barrier (e.g., 0.74 kN/m for UK building regs)",
            disabled=not include_barrier
        )
        st.session_state.inputs[f"{key_prefix}_barrier_knm"] = barrier_load_kn_per_m
        
        barrier_height_mm = parent.number_input(
            "Barrier height (mm)",
            min_value=0.0,
            max_value=2000.0,
            value=float(_get_default(f"{key_prefix}_barrier_height", 1100.0)),
            step=50.0,
            format="%.1f",
            key=f"{key_prefix}_barrier_height_widget",
            help="Height above mullion base where barrier load acts",
            disabled=not include_barrier
        )
        st.session_state.inputs[f"{key_prefix}_barrier_height"] = barrier_height_mm
        
        if include_barrier:
            # Display info (kN/m = N/mm, no conversion needed)
            barrier_n_per_mm = barrier_load_kn_per_m

    # ========== LOAD SUMMARY ==========
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
            f"{loading_inputs.wind_load_n_per_mm():.4f} N/mm" if include_wind else "Not included",
            help="Uniform distributed load from wind"
        )
    
    with sum_col2:
        parent.metric(
            "Barrier Load",
            f"{loading_inputs.barrier_load_n_per_mm():.4f} N/mm" if include_barrier else "Not included",
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
    
    # Total load (if both included)
    if include_wind or include_barrier:
        total_udl = loading_inputs.wind_load_n_per_mm() + loading_inputs.barrier_load_n_per_mm()
        parent.info(f"""
        **Combined uniform load:** {total_udl:.4f} N/mm ({total_udl * 1000:.2f} N/m)
        
        *This represents the total distributed load before applying load case factors*
        """)

    return loading_inputs

def loading_diagram_ui(container=None, key_prefix: str = "load",
                      span_mm: float = 4000.0,
                      bay_width_mm: float = 3000.0,
                      loading_inputs: Optional[LoadingInputs] = None):
    """
    Render 3D isometric diagram showing geometry and loading.
    
    Parameters
    ----------
    container : streamlit container, optional
        Container to render UI in (if None, uses st directly)
    key_prefix : str
        Prefix for session state keys
    span_mm : float
        Mullion span/length in mm
    bay_width_mm : float
        Bay width in mm
    loading_inputs : LoadingInputs, optional
        Loading configuration (if None, reads from session state)
    """
    try:
        import streamlit as st
        import plotly.graph_objects as go
        import numpy as np
    except Exception as e:
        raise RuntimeError("loading_diagram_ui requires streamlit and plotly") from e

    parent = container if container is not None else st
    
    # Get loading inputs if not provided
    if loading_inputs is None:
        if "inputs" not in st.session_state:
            return
        loading_inputs = LoadingInputs(
            include_wind=st.session_state.inputs.get(f"{key_prefix}_wind_en", True),
            wind_pressure_kpa=st.session_state.inputs.get(f"{key_prefix}_wind_kpa", 1.0),
            bay_width_mm=bay_width_mm,
            include_barrier=st.session_state.inputs.get(f"{key_prefix}_barrier_en", False),
            barrier_load_kn_per_m=st.session_state.inputs.get(f"{key_prefix}_barrier_knm", 0.74),
            barrier_height_mm=st.session_state.inputs.get(f"{key_prefix}_barrier_height", 1100.0)
        )
      
    # Scaling for visualization (target height ~7 units for consistency)
    target_height = 7.0
    scale = target_height / span_mm
    
    # Scaled dimensions
    height = span_mm * scale
    bay_width = bay_width_mm * scale
    total_width = 2 * bay_width  # Total diagram width (2x bay width as in TikZ)
    depth = height * 0.15  # Depth proportional to height
    mullion_width = height * 0.033  # Mullion width proportional to height
    barrier_height = loading_inputs.barrier_height_mm * scale if loading_inputs.include_barrier else 0
    
    # Create figure
    fig = go.Figure()
    
    # Define colors matching TikZ theme
    TT_light_blue = 'rgba(136,219,223,0.3)'
    TT_mid_blue = 'rgb(0,163,173)'
    TT_dark_blue = 'rgb(0,48,60)'
    TT_orange = 'rgb(211,69,29)'
    
    # ========== WIND LOAD SHADED AREA ==========
    if loading_inputs.include_wind:
        # Front face of wind load area (bay width centered in total width)
        x_left = total_width / 4
        x_right = 3 * total_width / 4
        
        # Front face
        fig.add_trace(go.Mesh3d(
            x=[x_left, x_right, x_right, x_left],
            y=[0, 0, 0, 0],
            z=[0, 0, height, height],
            color=TT_light_blue,
            opacity=0.4,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Back face
        fig.add_trace(go.Mesh3d(
            x=[x_left, x_right, x_right, x_left],
            y=[depth, depth, depth, depth],
            z=[0, 0, height, height],
            color=TT_light_blue,
            opacity=0.5,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Bottom face
        fig.add_trace(go.Mesh3d(
            x=[x_left, x_right, x_right, x_left],
            y=[0, 0, depth, depth],
            z=[0, 0, 0, 0],
            color=TT_light_blue,
            opacity=0.3,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Bay width dashed boundary lines
        fig.add_trace(go.Scatter3d(
            x=[x_left, x_left],
            y=[0, 0],
            z=[0, height],
            mode='lines',
            line=dict(color=TT_mid_blue, width=3, dash='dash'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter3d(
            x=[x_right, x_right],
            y=[0, 0],
            z=[0, height],
            mode='lines',
            line=dict(color=TT_mid_blue, width=3, dash='dash'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Wind load arrows distributed across the area
        arrow_positions_y = [0.15, 0.35, 0.55, 0.75, 0.95]
        arrow_positions_x = [0.3, 0.45, 0.6, 0.75]
        
        for y_frac in arrow_positions_y:
            for x_frac in arrow_positions_x:
                x_pos = x_frac * total_width
                z_pos = y_frac * height
                
                # Arrow shaft
                fig.add_trace(go.Scatter3d(
                    x=[x_pos, x_pos],
                    y=[0, depth * 0.67],
                    z=[z_pos, z_pos],
                    mode='lines',
                    line=dict(color=TT_mid_blue, width=2),
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                # Arrow head (cone)
                fig.add_trace(go.Cone(
                    x=[x_pos],
                    y=[depth * 0.67],
                    z=[z_pos],
                    u=[0],
                    v=[-0.3],
                    w=[0],
                    colorscale=[[0, TT_mid_blue], [1, TT_mid_blue]],
                    showscale=False,
                    sizemode='absolute',
                    sizeref=0.3,
                    showlegend=False,
                    hoverinfo='skip'
                ))
    
    # ========== MULLIONS (3 vertical box sections) ==========
    mullion_positions = [0, total_width / 2, total_width]
    
    for x_center in mullion_positions:
        x_left = x_center - mullion_width / 2
        x_right = x_center + mullion_width / 2
        
        # Front face
        fig.add_trace(go.Scatter3d(
            x=[x_left, x_right, x_right, x_left, x_left],
            y=[0, 0, 0, 0, 0],
            z=[0, 0, height, height, 0],
            mode='lines',
            line=dict(color=TT_dark_blue, width=4),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Side edges
        for x in [x_left, x_right]:
            fig.add_trace(go.Scatter3d(
                x=[x, x],
                y=[0, depth],
                z=[0, 0],
                mode='lines',
                line=dict(color=TT_dark_blue, width=3),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            fig.add_trace(go.Scatter3d(
                x=[x, x],
                y=[0, depth],
                z=[height, height],
                mode='lines',
                line=dict(color=TT_dark_blue, width=3),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Back face (lighter)
        fig.add_trace(go.Scatter3d(
            x=[x_left, x_right, x_right, x_left, x_left],
            y=[depth, depth, depth, depth, depth],
            z=[0, 0, height, height, 0],
            mode='lines',
            line=dict(color=TT_dark_blue, width=2),
            opacity=0.5,
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # ========== TRANSOMS (horizontal beams at top and bottom) ==========
    x_min = -mullion_width / 2
    x_max = total_width + mullion_width / 2
    
    for z_pos in [0, height]:  # Bottom and top
        # Front edge
        fig.add_trace(go.Scatter3d(
            x=[x_min, x_max],
            y=[0, 0],
            z=[z_pos, z_pos],
            mode='lines',
            line=dict(color=TT_dark_blue, width=4),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Side edges
        for x in [x_min, x_max]:
            fig.add_trace(go.Scatter3d(
                x=[x, x],
                y=[0, depth],
                z=[z_pos, z_pos],
                mode='lines',
                line=dict(color=TT_dark_blue, width=3),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Back edge
        fig.add_trace(go.Scatter3d(
            x=[x_min, x_max],
            y=[depth, depth],
            z=[z_pos, z_pos],
            mode='lines',
            line=dict(color=TT_dark_blue, width=3),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # ========== BARRIER LOAD ==========
    if loading_inputs.include_barrier and barrier_height > 0:
        x_left = total_width / 4
        x_right = 3 * total_width / 4
        arrow_length = depth * 1.33
        
        # Horizontal line load with arrows
        # Left arrow
        fig.add_trace(go.Scatter3d(
            x=[x_left, x_left],
            y=[0, arrow_length],
            z=[barrier_height, barrier_height],
            mode='lines',
            line=dict(color=TT_orange, width=5),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Cone(
            x=[x_left],
            y=[arrow_length],
            z=[barrier_height],
            u=[0],
            v=[-0.4],
            w=[0],
            colorscale=[[0, TT_orange], [1, TT_orange]],
            showscale=False,
            sizemode='absolute',
            sizeref=0.4,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Horizontal connecting line
        fig.add_trace(go.Scatter3d(
            x=[x_left, x_right],
            y=[arrow_length, arrow_length],
            z=[barrier_height, barrier_height],
            mode='lines',
            line=dict(color=TT_orange, width=5),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Right arrow
        fig.add_trace(go.Scatter3d(
            x=[x_right, x_right],
            y=[0, arrow_length],
            z=[barrier_height, barrier_height],
            mode='lines',
            line=dict(color=TT_orange, width=5),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Cone(
            x=[x_right],
            y=[arrow_length],
            z=[barrier_height],
            u=[0],
            v=[-0.4],
            w=[0],
            colorscale=[[0, TT_orange], [1, TT_orange]],
            showscale=False,
            sizemode='absolute',
            sizeref=0.4,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Dashed reference line at barrier height
        fig.add_trace(go.Scatter3d(
            x=[x_left, x_right],
            y=[0, 0],
            z=[barrier_height, barrier_height],
            mode='lines',
            line=dict(color=TT_orange, width=2, dash='dash'),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # ========== ANNOTATIONS ==========
    annotations = []
    
    # Bay width dimension
    annotations.append(dict(
        x=total_width / 2,
        y=0,
        z=-0.7,
        text=f"Bay width = {bay_width_mm:.0f} mm",
        showarrow=False,
        font=dict(size=12, color=TT_dark_blue)
    ))
    
    # Mullion length dimension
    annotations.append(dict(
        x=x_min - 0.5,
        y=0,
        z=height / 2,
        text=f"Length = {span_mm:.0f} mm",
        showarrow=False,
        font=dict(size=12, color=TT_dark_blue),
        textangle=-90
    ))
    
    # Wind load label
    if loading_inputs.include_wind:
        annotations.append(dict(
            x=total_width * 0.85,
            y=arrow_length + 1 if loading_inputs.include_barrier else depth + 1,
            z=height / 2,
            text=f"Wind: {loading_inputs.wind_pressure_kpa:.2f} kPa",
            showarrow=False,
            font=dict(size=12, color=TT_mid_blue)
        ))
    
    # Barrier load label
    if loading_inputs.include_barrier:
        annotations.append(dict(
            x=total_width / 2,
            y=arrow_length + 0.5,
            z=barrier_height,
            text=f"Barrier: {loading_inputs.barrier_load_kn_per_m:.2f} kN/m",
            showarrow=False,
            font=dict(size=12, color=TT_orange)
        ))
        
        # Barrier height dimension
        annotations.append(dict(
            x=total_width / 4 - 0.5,
            y=0,
            z=barrier_height / 2,
            text=f"{loading_inputs.barrier_height_mm:.0f} mm",
            showarrow=False,
            font=dict(size=11, color=TT_orange),
            textangle=-90
        ))
    
    # Update layout
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[x_min - 1, x_max + 1]),
            yaxis=dict(visible=False, range=[-1, depth + 3]),
            zaxis=dict(visible=False, range=[-1, height + 1]),
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2),
                center=dict(x=0, y=0, z=0)
            ),
            annotations=annotations
        ),
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        height=600,
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    parent.plotly_chart(fig, width="stretch")
    
    # Caption
    caption_parts = []
    if loading_inputs.include_wind:
        caption_parts.append(f"wind load ({loading_inputs.wind_pressure_kpa:.2f} kPa)")
    if loading_inputs.include_barrier:
        caption_parts.append(f"barrier load ({loading_inputs.barrier_load_kn_per_m:.2f} kN/m at {loading_inputs.barrier_height_mm:.0f} mm)")
    
    if caption_parts:
        caption = f"**Figure:** Loaded bay geometry showing {' and '.join(caption_parts)}. Bay width represents the tributary area for wind loading."
        parent.caption(caption)

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
