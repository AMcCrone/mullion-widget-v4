import streamlit as st
from inputs.geometry import geometry_ui
from inputs.material import material_ui, MaterialType
from inputs.loading import loading_ui, loading_diagram_ui, beam_model_diagram_ui
from inputs.load_cases import load_cases_ui
from analysis.beam_analysis import analyze_loadcase

st.set_page_config(page_title="Mullion Sizing")
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
load_cases = load_cases_ui(container=st, key_prefix="main_load_cases")
st.markdown("---")

st.header("Results")
results = analyze_loadcase(span_mm=geom.span_mm,loads=load_case.loads,E=mat.E,I=section.I)
# Use results for plotting and checks
st.line_chart({"V(x)": results['V_N']})
st.metric("Max Moment", f"{results['M_max_Nm']:.2f} N·m")
st.metric("Max Deflection", f"{results['v_max_m']*1000:.2f} mm")
