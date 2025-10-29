# input/material.py
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class MaterialType(str, Enum):
    STEEL = "Steel"
    ALUMINIUM = "Aluminium"


# Example default property sets. You said you'll populate alloys later;
# these are sensible defaults you can edit in data files later.
_DEFAULT_MATERIAL_LIBRARY: Dict[MaterialType, Dict[str, Dict]] = {
    MaterialType.STEEL: {
        "S275": {
            "E": 210e9,         # Pa
            "density": 7850.0,  # kg/m3
            "fy": 275e6,        # Pa
            "fu": 430e6,        # Pa (approx)
        },
        "S355": {
            "E": 210e9,
            "density": 7850.0,
            "fy": 355e6,
            "fu": 510e6,
        },
    },
    MaterialType.ALUMINIUM: {
        "6063-T6": {
            "E": 69e9,          # Pa
            "density": 2700.0,  # kg/m3
            "fy": 155e6,        # Pa (example)
            "fu": 200e6,
        },
        "6082-T6": {
            "E": 69e9,
            "density": 2700.0,
            "fy": 260e6,
            "fu": 310e6,
        },
    },
}


@dataclass
class Material:
    """Material properties object.

    Units:
      - E: Pa (N/m^2)
      - density: kg/m^3
      - fy, fu: Pa
    """
    material_type: MaterialType
    grade: str
    E: float           # Pa
    density: float     # kg/m3
    fy: float          # Pa
    fu: float          # Pa

    def __post_init__(self):
        if self.E <= 0:
            raise ValueError("E must be positive (Pa).")
        if self.density <= 0:
            raise ValueError("density must be positive (kg/m3).")
        if self.fy <= 0:
            raise ValueError("fy must be positive (Pa).")
        if self.fu <= 0:
            raise ValueError("fu must be positive (Pa).")

    @classmethod
    def from_library(cls, material_type: MaterialType, grade: str) -> "Material":
        """Create material using the built-in small library."""
        lib = _DEFAULT_MATERIAL_LIBRARY.get(material_type, {})
        props = lib.get(grade)
        if props is None:
            raise KeyError(f"Grade '{grade}' not found for material type {material_type}.")
        return cls(
            material_type=material_type,
            grade=grade,
            E=props["E"],
            density=props["density"],
            fy=props["fy"],
            fu=props["fu"],
        )

    @staticmethod
    def available_grades(material_type: MaterialType):
        return list(_DEFAULT_MATERIAL_LIBRARY.get(material_type, {}).keys())


# Streamlit UI helper (keeps streamlit import local to this function)
def material_ui(default_type: MaterialType = MaterialType.ALUMINIUM,
                default_grade: Optional[str] = None) -> Material:
    """
    Display a small Streamlit UI to pick material type and grade and return a Material object.
    Call this inside your Streamlit main when you want to collect material input.

    Example:
        material = material_ui()
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("material_ui requires streamlit but it isn't available.") from e

    st.sidebar.header("Material")
    mtype = st.sidebar.selectbox("Material type", list(MaterialType), index=list(MaterialType).index(default_type))
    grades = Material.available_grades(mtype)
    if not grades:
        st.sidebar.error(f"No grades configured for {mtype}. Edit _DEFAULT_MATERIAL_LIBRARY.")
        grade = st.sidebar.text_input("Grade (free text)", value=default_grade or "")
        # Provide more fields for manual input if library is empty
        E = st.sidebar.number_input("E (Pa)", value=69e9 if mtype == MaterialType.ALUMINIUM else 210e9)
        density = st.sidebar.number_input("Density (kg/m3)", value=2700.0 if mtype == MaterialType.ALUMINIUM else 7850.0)
        fy = st.sidebar.number_input("fy (Pa)", value=155e6 if mtype == MaterialType.ALUMINIUM else 275e6)
        fu = st.sidebar.number_input("fu (Pa)", value=200e6 if mtype == MaterialType.ALUMINIUM else 430e6)
        return Material(material_type=mtype, grade=grade, E=E, density=density, fy=fy, fu=fu)

    default_idx = 0
    if default_grade and default_grade in grades:
        default_idx = grades.index(default_grade)
    grade = st.sidebar.selectbox("Grade / alloy", grades, index=default_idx)
    # create from library
    mat = Material.from_library(mtype, grade)
    st.sidebar.markdown(f"**E**: {mat.E:.2e} Pa  •  **fy**: {mat.fy:.2e} Pa")
    return mat

