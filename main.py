# src/app/main.py (snippet)
import streamlit as st
from input.geometry import geometry_ui
from input.material import material_ui, MaterialType
from input.loading import loading_ui

st.set_page_config(page_title="Mullion Sizing")
st.title("Mullion Sizing)")

# Layout example: put geometry and material side-by-side, loads on a second row
geom = geometry_ui(container=st, key_prefix="main_geom", default_span_mm=3000, default_bay_width_mm=1000)
mat = material_ui(container=st, key_prefix="main_mat", default_type=MaterialType.ALUMINIUM)

# loads in full width below
load_case = loading_ui(container=st, key_prefix="main_load")

st.markdown("---")
st.header("Summary")
st.write("Geometry:", geom.as_dict())
st.write("Material:", {"type": mat.material_type.value, "grade": mat.grade, "E (Pa)": mat.E})
st.write("Load case:", {"name": load_case.name, "case_type": load_case.case_type})
st.write("Loads list:", load_case.loads)

if st.button("Run analysis"):
    st.success("Now you can call analysis modules with these dataclasses.")
