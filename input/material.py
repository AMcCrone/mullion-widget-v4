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

def material_ui(container=None, key_prefix: str = "mat",
                default_type: "MaterialType" = None, default_grade: str | None = None) -> "Material":
    """
    Render material selection on the main page (not sidebar) and return a Material instance.

    Parameters:
    - container: Streamlit container (defaults to st)
    - key_prefix: unique widget key prefix
    - default_type: optional default MaterialType (if None, the first enum value is used)
    - default_grade: optional default grade string

    Returns:
    - Material dataclass instance (either from library or user-specified)
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("material_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    # determine default material type if not provided
    default_type = default_type if default_type is not None else list(MaterialType)[0]

    with parent.expander("Material", expanded=False):
        mtype = parent.selectbox(
            "Material type",
            options=list(MaterialType),
            index=list(MaterialType).index(default_type),
            format_func=lambda mt: mt.value,
            key=f"{key_prefix}_type"
        )

        # get available grades for the selected type
        grades = Material.available_grades(mtype)
        # allow "Custom" as an option if library available (so user can type numeric properties)
        grade_options = grades.copy()
        grade_options.insert(0, "Custom")  # "Custom" option to enter raw E/density/fy/fu

        # select grade
        default_idx = 1 if (default_grade is None or default_grade not in grades) else grade_options.index(default_grade)
        selected_grade = parent.selectbox(
            "Grade / alloy",
            options=grade_options,
            index=default_idx,
            key=f"{key_prefix}_grade"
        )

        if selected_grade == "Custom":
            parent.markdown("Enter custom material properties:")
            E = parent.number_input("E (Pa)", value=69e9 if mtype == MaterialType.ALUMINIUM else 210e9,
                                    format="%.6e", key=f"{key_prefix}_E")
            density = parent.number_input("Density (kg/m³)",
                                          value=2700.0 if mtype == MaterialType.ALUMINIUM else 7850.0,
                                          format="%.3f", key=f"{key_prefix}_density")
            fy = parent.number_input("fy (Pa)", value=155e6 if mtype == MaterialType.ALUMINIUM else 275e6,
                                     format="%.3e", key=f"{key_prefix}_fy")
            fu = parent.number_input("fu (Pa)", value=200e6 if mtype == MaterialType.ALUMINIUM else 430e6,
                                     format="%.3e", key=f"{key_prefix}_fu")
            mat = Material(material_type=mtype, grade="Custom", E=E, density=density, fy=fy, fu=fu)
        else:
            # create from library
            try:
                mat = Material.from_library(mtype, selected_grade)
            except KeyError:
                parent.error(f"Grade '{selected_grade}' not found in library; switch to Custom to enter properties.")
                # fallback to a minimal custom set so function always returns something
                mat = Material(material_type=mtype, grade="CustomFallback",
                               E=69e9 if mtype == MaterialType.ALUMINIUM else 210e9,
                               density=2700.0 if mtype == MaterialType.ALUMINIUM else 7850.0,
                               fy=155e6 if mtype == MaterialType.ALUMINIUM else 275e6,
                               fu=200e6 if mtype == MaterialType.ALUMINIUM else 430e6)

        # show summary
        parent.write(f"**Selected:** {mat.material_type.value} — {mat.grade}")
        parent.write(f"E = {mat.E:.2e} Pa • fy = {mat.fy:.2e} Pa • density = {mat.density:.1f} kg/m³")

    return mat
