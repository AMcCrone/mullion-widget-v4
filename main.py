import streamlit as st

from input.geometry import geometry_ui, Geometry
from input.material import material_ui, Material, MaterialType
from input.loading import loading_ui, LoadCase

st.title("Mullion sizing — demo input page")

# UI helpers return dataclass instances
geometry: Geometry = geometry_ui(default_span_mm=3000, default_bay_width_mm=1000)
material: Material = material_ui(default_type=MaterialType.ALUMINIUM)
load_case: LoadCase = loading_ui()

st.header("Summary")
st.write("Geometry:", geometry.as_dict())
st.write("Material:", {"type": material.material_type, "grade": material.grade, "E (Pa)": material.E})
st.write("Load case:", {"name": load_case.name, "case_type": load_case.case_type})
st.write("Loads list:", load_case.loads)

# When you call your analysis functions, use geometry.span_m and load_case.total_uniform_n_per_m()
if st.button("Run analysis (placeholder)"):
    span_m = geometry.span_m
    w_total_N_per_m = load_case.total_uniform_n_per_m()
    st.write(f"Span (m): {span_m:.3f}, Uniform load (N/m): {w_total_N_per_m:.1f}")
    # call your analysis functions here...
    st.success("Would now call analysis modules with these inputs.")
