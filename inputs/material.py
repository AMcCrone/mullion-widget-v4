# input/material.py
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class MaterialType(str, Enum):
    STEEL = "Steel"
    ALUMINIUM = "Aluminium"

_DEFAULT_MATERIAL_LIBRARY: Dict[MaterialType, Dict[str, Dict]] = {
    MaterialType.STEEL: {
        # Common EN structural steels
        "S235": {"E": 210e9, "density": 7850.0, "fy": 235e6},
        "S275": {"E": 210e9, "density": 7850.0, "fy": 275e6},
        "S355": {"E": 210e9, "density": 7850.0, "fy": 355e6},
        "S420": {"E": 210e9, "density": 7850.0, "fy": 420e6},
        "S460": {"E": 210e9, "density": 7850.0, "fy": 460e6},
    },
    MaterialType.ALUMINIUM: {
        # Common architectural extrusions and structural alloys
        "6063-T5": {"E": 70e9, "density": 2700.0, "fy": 130e6},
        "6063-T6": {"E": 70e9, "density": 2700.0, "fy": 160e6},
        "6061-T6": {"E": 70e9, "density": 2700.0, "fy": 140e6},
        "6005A-T6": {"E": 70e9, "density": 2700.0, "fy": 225e6},
        "6082-T6": {"E": 70e9, "density": 2700.0, "fy": 250e6},
    },
}

@dataclass
class Material:
    material_type: MaterialType
    grade: str
    E: float
    density: float
    fy: float

    def __post_init__(self):
        if self.E <= 0:
            raise ValueError("E must be positive (Pa).")
        if self.density <= 0:
            raise ValueError("density must be positive (kg/m3).")
        if self.fy <= 0:
            raise ValueError("fy must be positive (Pa).")

    @classmethod
    def from_library(cls, material_type: MaterialType, grade: str) -> "Material":
        lib = _DEFAULT_MATERIAL_LIBRARY.get(material_type, {})
        props = lib.get(grade)
        if props is None:
            raise KeyError(f"Grade '{grade}' not found for material type {material_type}.")
        return cls(material_type=material_type, grade=grade, **props)

    @staticmethod
    def available_grades(material_type: MaterialType):
        return list(_DEFAULT_MATERIAL_LIBRARY.get(material_type, {}).keys())


# ---------- UI helper (always-visible inputs, two-column) ----------
def material_ui(container=None, key_prefix: str = "mat",
                default_type: Optional[MaterialType] = None, default_grade: Optional[str] = None) -> Material:
    """
    Render material inputs directly on the page (always visible) and return a Material instance.

    Uses st.session_state.inputs[...] to persist values.
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("material_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    # Ensure state dict
    if "inputs" not in st.session_state:
        st.session_state.inputs = {}

    def _get_default(name, fallback):
        return st.session_state.inputs.get(name, fallback)

    default_type = default_type if default_type is not None else list(MaterialType)[0]

    # Layout columns: left -> selection, right -> properties summary / manual entries
    col1, col2 = parent.columns(2)

    with col1:
        mtype = parent.selectbox(
            "Material type",
            options=list(MaterialType),
            index=list(MaterialType).index(_get_default(f"{key_prefix}_type", default_type)),
            format_func=lambda mt: mt.value,
            key=f"{key_prefix}_type_widget"
        )
        st.session_state.inputs[f"{key_prefix}_type"] = mtype

    with col2:
        # grade select, include "Custom"
        grades = Material.available_grades(mtype)
        grade_options = ["Custom"] + grades
        default_grade_idx = 0
        saved_grade = _get_default(f"{key_prefix}_grade", default_grade)
        if saved_grade in grade_options:
            default_grade_idx = grade_options.index(saved_grade)
        selected_grade = parent.selectbox("Grade / alloy", options=grade_options, index=default_grade_idx, key=f"{key_prefix}_grade_widget")
        st.session_state.inputs[f"{key_prefix}_grade"] = selected_grade
        
    if selected_grade == "Custom":
        parent.markdown("Enter custom properties:")
        col1, col2, col3 = parent.columns(3)
        with col1:
            E = parent.number_input("E (Pa)", value=float(_get_default(f"{key_prefix}_E", 70e9 if mtype == MaterialType.ALUMINIUM else 210e9)), format="%.2e", key=f"{key_prefix}_E_widget")
        with col2:
            density = parent.number_input("Density (kg/m³)", value=float(_get_default(f"{key_prefix}_density", 2700.0 if mtype == MaterialType.ALUMINIUM else 7850.0)), format="%.0f", key=f"{key_prefix}_density_widget")
        with col3:
            fy = parent.number_input("fy (Pa)", value=float(_get_default(f"{key_prefix}_fy", 160e6 if mtype == MaterialType.ALUMINIUM else 275e6)), format="%.2e", key=f"{key_prefix}_fy_widget")

        # save to session
        st.session_state.inputs[f"{key_prefix}_E"] = E
        st.session_state.inputs[f"{key_prefix}_density"] = density
        st.session_state.inputs[f"{key_prefix}_fy"] = fy

        mat = Material(material_type=mtype, grade="Custom", E=E, density=density, fy=fy)
    else:
        # try library
        try:
            mat = Material.from_library(mtype, selected_grade)
        except KeyError:
            parent.error("Selected grade not found; switch to Custom to enter properties.")
            # fallback
            mat = Material(material_type=mtype, grade="CustomFallback",
                           E=70e9 if mtype == MaterialType.ALUMINIUM else 210e9,
                           density=2700.0 if mtype == MaterialType.ALUMINIUM else 7850.0,
                           fy=160e6 if mtype == MaterialType.ALUMINIUM else 275e6)

    # Save primary selections to session_state for persistence
    st.session_state.inputs[f"{key_prefix}_type"] = mtype
    st.session_state.inputs[f"{key_prefix}_grade"] = selected_grade

    parent.write(f"Elastic Modulus, E: {mat.E:.3e} Pa, Yield Stress, fy: {mat.fy:.3e} Pa, Density: {mat.density:.1f} kg/m³")

    return mat
