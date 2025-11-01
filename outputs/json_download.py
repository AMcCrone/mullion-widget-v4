import json
import streamlit as st
from datetime import datetime
from typing import Dict, Any

def create_design_json(
    geom,
    mat,
    loading_inputs,
    load_case_set,
    deflection_limit_mm: float,
    deflection_criteria: str,
    safety_factor: float,
    sigma_allow_Pa: float,
    uls_results: Dict,
    sls_results: Dict,
    Z_req: float,
    I_req: float
) -> Dict[str, Any]:
    """
    Extract all key design variables into a JSON-serializable dictionary.
    
    Parameters
    ----------
    geom : Geometry
        Geometry dataclass instance
    mat : Material
        Material dataclass instance
    loading_inputs : LoadingInputs
        Loading inputs dataclass instance
    load_case_set : LoadCaseSet
        Load case set dataclass instance
    deflection_limit_mm : float
        Deflection limit in mm
    deflection_criteria : str
        Deflection criteria type (e.g., "CWCT Criteria", "Custom")
    safety_factor : float
        Material safety factor (γ_M)
    sigma_allow_Pa : float
        Allowable stress in Pa
    uls_results : Dict
        ULS analysis results dictionary
    sls_results : Dict
        SLS analysis results dictionary
    Z_req : float
        Required section modulus in m³
    I_req : float
        Required moment of inertia in m⁴
    
    Returns
    -------
    Dict[str, Any]
        JSON-serializable dictionary with all design data
    """
    
    # Extract governing ULS values
    gov_M_case, gov_M_val = uls_results['governing']['M_max']
    gov_V_case, gov_V_val = uls_results['governing']['V_max']
    
    # Extract governing SLS values
    gov_sls_case = sls_results['governing']['case']
    
    # Build the JSON structure
    design_data = {
        "metadata": {
            "report_generated": datetime.now().isoformat(),
            "app_name": "TT Mullion Sizing App",
            "version": "1.0"
        },
        
        "geometry": {
            "span_mm": geom.span_mm,
            "span_m": geom.span_m,
            "bay_width_mm": geom.bay_width_mm,
            "bay_width_m": geom.bay_width_m,
            "tributary_area_m2": geom.tributary_area_m2
        },
        
        "material": {
            "type": mat.material_type.value,
            "grade": mat.grade,
            "elastic_modulus_Pa": mat.E,
            "elastic_modulus_GPa": mat.E / 1e9,
            "yield_strength_Pa": mat.fy,
            "yield_strength_MPa": mat.fy / 1e6,
            "density_kg_m3": mat.density
        },
        
        "loading": {
            "include_wind": getattr(loading_inputs, 'include_wind', False),
            "wind_pressure_kPa": getattr(loading_inputs, 'wind_pressure_kpa', 0),
            "wind_pressure_Pa": getattr(loading_inputs, 'wind_pressure_kpa', 0) * 1000 if getattr(loading_inputs, 'include_wind', False) else 0,
            "include_barrier": getattr(loading_inputs, 'include_barrier', False),
            "barrier_load_kN_m": getattr(loading_inputs, 'barrier_load_kn_per_m', 0),
            "barrier_load_N_m": getattr(loading_inputs, 'barrier_load_kn_per_m', 0) * 1000 if getattr(loading_inputs, 'include_barrier', False) else 0,
            "barrier_height_mm": getattr(loading_inputs, 'barrier_height_mm', 1100),
        },
        
        "load_cases": {
            "uls_cases": [
                {
                    "name": case.name,
                    "wind_factor": case.wind_factor,
                    "barrier_factor": case.barrier_factor
                }
                for case in load_case_set.uls_cases
            ],
            "sls_cases": [
                {
                    "name": case.name,
                    "wind_factor": case.wind_factor,
                    "barrier_factor": case.barrier_factor
                }
                for case in load_case_set.sls_cases
            ]
        },
        
        "design_criteria": {
            "deflection": {
                "criteria_type": deflection_criteria,
                "limit_mm": deflection_limit_mm,
                "limit_ratio": geom.span_mm / deflection_limit_mm
            },
            "material_safety": {
                "safety_factor": safety_factor,
                "allowable_stress_Pa": sigma_allow_Pa,
                "allowable_stress_MPa": sigma_allow_Pa / 1e6
            }
        },
        
        "uls_results": {
            "governing_moment": {
                "case": gov_M_case,
                "value_Nm": gov_M_val,
                "value_kNm": gov_M_val / 1000
            },
            "governing_shear": {
                "case": gov_V_case,
                "value_N": gov_V_val,
                "value_kN": gov_V_val / 1000
            },
            "reactions": {
                case_name: {
                    "RA_N": case_data['RA_N'],
                    "RA_kN": case_data['RA_N'] / 1000,
                    "RB_N": case_data['RB_N'],
                    "RB_kN": case_data['RB_N'] / 1000,
                    "M_max_Nm": case_data['M_max_Nm'],
                    "M_max_kNm": case_data['M_max_Nm'] / 1000,
                    "V_max_N": case_data['V_max_N'],
                    "V_max_kN": case_data['V_max_N'] / 1000
                }
                for case_name, case_data in uls_results['cases'].items()
            }
        },
        
        "sls_results": {
            "deflection_limit_mm": sls_results['governing']['v_limit_mm'],
            "governing_case": gov_sls_case,
            "required_I_m4": I_req,
            "required_I_cm4": I_req * 1e8,
            "cases": {
                case_name: {
                    "I_req_m4": case_data['I_req_m4'],
                    "I_req_cm4": case_data['I_req_m4'] * 1e8,
                    "unit_deflection_m": case_data['v_unit_max_m'],
                    "unit_deflection_mm": case_data['v_unit_max_m'] * 1000
                }
                for case_name, case_data in sls_results['cases'].items()
            }
        },
        
        "design_requirements": {
            "section_modulus": {
                "required_m3": Z_req,
                "required_cm3": Z_req * 1e6,
                "governing_case": gov_M_case
            },
            "moment_of_inertia": {
                "required_m4": I_req,
                "required_cm4": I_req * 1e8,
                "governing_case": gov_sls_case
            }
        }
    }
    
    return design_data


def add_json_download_button(
    design_data: Dict[str, Any],
    filename: str = "mullion_design.json",
    button_label: str = "📥 Download Design JSON"
):
    """
    Add a download button to the Streamlit sidebar for the design JSON.
    
    Parameters
    ----------
    design_data : Dict[str, Any]
        The design data dictionary to export
    filename : str
        The filename for the downloaded JSON file
    button_label : str
        The label for the download button
    """
    json_string = json.dumps(design_data, indent=2)
    
    st.sidebar.download_button(
        label=button_label,
        data=json_string,
        file_name=filename,
        mime="application/json",
        help="Download design data as JSON for report generation"
    )
