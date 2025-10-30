import streamlit as st
from inputs.geometry import geometry_ui
from inputs.material import material_ui, MaterialType
from inputs.loading import loading_ui, loading_diagram_ui, beam_model_diagram_ui
from inputs.load_cases import load_cases_ui
from analysis.beam_analysis import analyze_uls_cases, analyze_sls_deflection_requirement, compute_required_section_modulus

import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="TT Mullion Sizing App")
st.title("Mullion Sizing App")

# Layout example: put geometry and material side-by-side, loads on a second row
st.header("Geometry")
geom = geometry_ui(container=st, key_prefix="main_geom", default_span_mm=4000, default_bay_width_mm=3000)
st.markdown("---")

st.header("Material")
mat = material_ui(container=st, key_prefix="main_mat", default_type=MaterialType.ALUMINIUM)
st.markdown("---")

st.header("Loading")
# Get geometry from session state using the CORRECT keys with the key_prefix
span_mm = st.session_state.inputs.get("main_geom_span_mm", 3000.0)
bay_width_mm = st.session_state.inputs.get("main_geom_bay_width_mm", 1000.0)

# Get loading inputs (only call once)
loading_inputs = loading_ui(container=st, key_prefix="main_load", bay_width_mm=bay_width_mm)

# Display diagram using the same loading_inputs
loading_diagram_ui(container=st,key_prefix="main_load",span_mm=span_mm,bay_width_mm=bay_width_mm,loading_inputs=loading_inputs)
# Display diagram using the same loading_inputs
beam_model_diagram_ui(span_mm=span_mm,loading_inputs=loading_inputs)
st.markdown("---")

st.header("Load Cases")
load_case_set = load_cases_ui(container=st, key_prefix="main_load_cases")
st.markdown("---")

# ========== DESIGN CRITERIA ==========
st.header("Design Criteria")

col1, col2, col3 = st.columns(3)

with col1:
    deflection_limit_mm = st.number_input(
        "Deflection Limit (mm)",
        value=geom.span_mm / 250,  # Default L/250
        min_value=1.0,
        format="%.2f",
        help="Maximum allowable deflection for SLS"
    )
    st.caption(f"≈ L/{geom.span_mm/deflection_limit_mm:.0f}")

with col2:
    safety_factor = st.number_input(
        "Safety Factor for Bending",
        value=1.5,
        min_value=1.0,
        max_value=3.0,
        step=0.1,
        format="%.2f",
        help="Applied to yield stress to get allowable stress"
    )

with col3:
    sigma_allow_Pa = mat.fy / safety_factor
    st.metric(
        "Allowable Stress",
        f"{sigma_allow_Pa/1e6:.1f} MPa",
        help="σ_allow = fy / γ"
    )

st.markdown("---")

# ========== ANALYSIS ==========
st.header("Results")

# Run analyses
with st.spinner("⏳ Analyzing load cases..."):
    uls_results = analyze_uls_cases(geom, loading_inputs, load_case_set)
    sls_results = analyze_sls_deflection_requirement(
        geom, loading_inputs, load_case_set, mat.E, deflection_limit_mm
    )

# ========================================
# ULS ANALYSIS
# ========================================
st.subheader("Ultimate Limit State (ULS)")

# Governing values summary
st.markdown("#### Governing Values")
col1, col2, col3 = st.columns(3)

gov_M_case, gov_M_val = uls_results['governing']['M_max']
gov_V_case, gov_V_val = uls_results['governing']['V_max']

with col1:
    st.metric(
        "Max Bending Moment",
        f"{gov_M_val/1000:.2f} kN·m",
        help=f"Governing case: {gov_M_case}"
    )
    st.caption(f"📌 {gov_M_case}")

with col2:
    st.metric(
        "Max Shear Force",
        f"{gov_V_val/1000:.2f} kN",
        help=f"Governing case: {gov_V_case}"
    )
    st.caption(f"📌 {gov_V_case}")

with col3:
    Z_req = compute_required_section_modulus(gov_M_val, sigma_allow_Pa)
    st.metric(
        "Required Section Modulus",
        f"{Z_req*1e6:.2f} cm³",
        help="Z_req = M_max / σ_allow"
    )

st.markdown("---")

# Reactions table
st.markdown("#### Reactions for All ULS Cases")
reaction_data = []
for case_name, case_data in uls_results['cases'].items():
    reaction_data.append({
        "Load Case": case_name,
        "RA (kN)": f"{case_data['RA_N']/1000:.2f}",
        "RB (kN)": f"{case_data['RB_N']/1000:.2f}",
        "M_max (kN·m)": f"{case_data['M_max_Nm']/1000:.2f}",
        "V_max (kN)": f"{case_data['V_max_N']/1000:.2f}"
    })

st.dataframe(reaction_data, use_container_width=True, hide_index=True)

st.markdown("---")

# Shear Force Diagram with dropdown
st.markdown("#### Shear Force Diagram")

# Case selector - default to governing
case_options = list(uls_results['cases'].keys())
default_V_idx = case_options.index(gov_V_case) if gov_V_case in case_options else 0

selected_V_case = st.selectbox(
    "Select ULS case for shear diagram:",
    options=case_options,
    index=default_V_idx,
    key="uls_V_selector"
)

# Plot shear diagram
V_data = uls_results['cases'][selected_V_case]
fig_V = go.Figure()
fig_V.add_trace(go.Scatter(
    x=V_data['x_m'],
    y=V_data['V_N']/1000,
    mode='lines',
    name='Shear Force',
    line=dict(color='#e74c3c', width=2),
    fill='tozeroy',
    fillcolor='rgba(231, 76, 60, 0.2)'
))

fig_V.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

fig_V.update_layout(
    title=f"Shear Force Diagram - {selected_V_case}",
    xaxis_title="Position along span (m)",
    yaxis_title="Shear Force (kN)",
    height=400,
    hovermode='x unified',
    showlegend=False
)

st.plotly_chart(fig_V, use_container_width=True)

# Show max value for selected case
col1, col2 = st.columns(2)
with col1:
    st.metric("Max V (this case)", f"{V_data['V_max_N']/1000:.2f} kN")
with col2:
    st.metric("Location", f"{V_data['x_Vmax_m']:.3f} m")

st.markdown("---")

# Bending Moment Diagram with dropdown
st.markdown("#### Bending Moment Diagram")

# Case selector - default to governing
default_M_idx = case_options.index(gov_M_case) if gov_M_case in case_options else 0

selected_M_case = st.selectbox(
    "Select ULS case for moment diagram:",
    options=case_options,
    index=default_M_idx,
    key="uls_M_selector"
)

# Plot moment diagram
M_data = uls_results['cases'][selected_M_case]
fig_M = go.Figure()
fig_M.add_trace(go.Scatter(
    x=M_data['x_m'],
    y=M_data['M_Nm']/1000,
    mode='lines',
    name='Bending Moment',
    line=dict(color='#3498db', width=2),
    fill='tozeroy',
    fillcolor='rgba(52, 152, 219, 0.2)'
))

fig_M.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

fig_M.update_layout(
    title=f"Bending Moment Diagram - {selected_M_case}",
    xaxis_title="Position along span (m)",
    yaxis_title="Bending Moment (kN·m)",
    height=400,
    hovermode='x unified',
    showlegend=False
)

st.plotly_chart(fig_M, use_container_width=True)

# Show max value for selected case
col1, col2 = st.columns(2)
with col1:
    st.metric("Max M (this case)", f"{M_data['M_max_Nm']/1000:.2f} kN·m")
with col2:
    st.metric("Location", f"{M_data['x_Mmax_m']:.3f} m")

st.markdown("---")

# ========================================
# SLS ANALYSIS
# ========================================
st.subheader("Serviceability Limit State (SLS)")

st.markdown("#### Deflection Requirements")

# Summary of SLS results
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Deflection Limit",
        f"{sls_results['governing']['v_limit_mm']:.2f} mm",
        help=f"L/{geom.span_mm/sls_results['governing']['v_limit_mm']:.0f}"
    )

with col2:
    I_req = sls_results['governing']['I_req_m4']
    st.metric(
        "Required I",
        f"{I_req*1e8:.2f} cm⁴",
        help="Second moment of area needed to satisfy deflection limit"
    )

with col3:
    gov_sls_case = sls_results['governing']['case']
    st.metric(
        "Governing Case",
        gov_sls_case,
        help="SLS case requiring largest I"
    )

st.markdown("---")

# Detailed SLS results table
st.markdown("#### All SLS Cases - Required I")
sls_data = []
for case_name, case_data in sls_results['cases'].items():
    is_governing = "✓" if case_name == gov_sls_case else ""
    sls_data.append({
        "Load Case": case_name,
        "Required I (cm⁴)": f"{case_data['I_req_m4']*1e8:.2f}",
        "Unit Deflection (mm)": f"{case_data['v_unit_max_m']*1000:.3f}",
        "Governing": is_governing
    })

st.dataframe(sls_data, use_container_width=True, hide_index=True)

st.caption("💡 Unit deflection is the max deflection that would occur with I = 1.0 m⁴")

st.markdown("---")

# ========================================
# FINAL DESIGN SUMMARY
# ========================================
st.header("Design Summary")

st.markdown("""
Select a section with properties that meet or exceed the following requirements:
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Strength (ULS)")
    st.metric("Minimum Z required", f"{Z_req*1e6:.2f} cm³")
    st.caption(f"Based on {gov_M_case}")

with col2:
    st.markdown("### Stiffness (SLS)")
    st.metric("Minimum I required", f"{I_req*1e8:.2f} cm⁴")
    st.caption(f"Based on {gov_sls_case}")

st.info("""
**Next steps:**
1. Select a standard section (e.g., from a manufacturer catalog) that satisfies both Z ≥ Z_req and I ≥ I_req
2. Verify shear capacity if needed (not checked in this tool)
3. Check local buckling and connection details per applicable code
""")
