"""
Beam Analysis Module for Simply-Supported Beams
================================================

This module provides beam analysis functions for simply-supported beams under
arbitrary combinations of uniform and point loads.

Unit Conventions:
-----------------
- Input: span in mm, uniform loads in N/mm (as stored), point loads in N
- Internal: all converted to SI (m, N, N/m)
- Output: x in m, V in N, M in N·m, v in m

Example Usage:
--------------
```python
from input.geometry import Geometry
from input.loading import LoadingInputs
from input.material import Material, MaterialType
from input.load_cases import LoadCaseSet
from beam_analysis import analyze_uls_cases, analyze_sls_deflection_requirement

# Setup inputs
geom = Geometry(span_mm=3000, bay_width_mm=1000)
mat = Material.from_library(MaterialType.ALUMINIUM, "6063-T6")
loading_inputs = LoadingInputs(...)
load_case_set = LoadCaseSet.create_en1990_defaults()

# Analyze ULS (get M, V for all cases)
uls_results = analyze_uls_cases(geom, loading_inputs, load_case_set)

# Analyze SLS (get required I for deflection limit)
sls_results = analyze_sls_deflection_requirement(
    geom, loading_inputs, load_case_set, mat.E, deflection_limit_mm=20.0
)
```
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass


def compute_wind_barrier_uniform_and_point(
    span_mm: float,
    loads: List,
    n_points: int = 501
) -> Dict[str, np.ndarray]:
    """
    Compute reactions, shear force V(x), and bending moment M(x) for a simply-supported
    beam under arbitrary uniform and point loads.
    
    Parameters:
    -----------
    span_mm : float
        Span length in millimeters
    loads : List[Load]
        List of Load objects with attributes:
        - distribution: 'uniform' or 'point'
        - magnitude: float (N/mm for uniform, N for point)
        - height_mm: Optional[float] (not used in analysis, for visualization only)
    n_points : int
        Number of points for discretization (default 501)
    
    Returns:
    --------
    dict with keys:
        - 'x_m': np.ndarray, position array in metres
        - 'V': np.ndarray, shear force in N
        - 'M': np.ndarray, bending moment in N·m
        - 'RA': float, left reaction in N
        - 'RB': float, right reaction in N
    """
    # Convert span to metres
    L = span_mm / 1000.0  # m
    
    # Create position array
    x_m = np.linspace(0, L, n_points)
    
    # Separate loads into uniform and point
    uniform_loads = []
    point_loads = []
    
    for load in loads:
        if load.distribution == 'uniform':
            # Convert N/mm to N/m
            w_Npm = load.magnitude * 1000.0
            uniform_loads.append(w_Npm)
        elif load.distribution == 'point':
            # Point load already in N
            P_N = load.magnitude
            # Assume point loads are applied at midspan unless specified
            a_m = L / 2.0
            point_loads.append((P_N, a_m))
    
    # Compute reactions using equilibrium
    W_total = sum(w * L for w in uniform_loads)
    P_total = sum(P for P, a in point_loads)
    total_load = W_total + P_total
    
    # Moment equilibrium about left support to find RB
    moment_uniform = sum(w * L * (L / 2.0) for w in uniform_loads)
    moment_point = sum(P * a for P, a in point_loads)
    total_moment = moment_uniform + moment_point
    
    # Solve for reactions
    if L > 0:
        RB = total_moment / L
        RA = total_load - RB
    else:
        RA = RB = 0.0
    
    # Compute shear force V(x)
    V = np.zeros_like(x_m)
    
    for i, x in enumerate(x_m):
        V[i] = RA
        
        # Subtract contribution from uniform loads
        for w in uniform_loads:
            V[i] -= w * x
        
        # Subtract point loads that have been passed
        for P, a in point_loads:
            if x >= a:
                V[i] -= P
    
    # Compute bending moment M(x) by integrating V(x)
    dx = x_m[1] - x_m[0]
    M = np.zeros_like(x_m)
    M[0] = 0.0
    
    for i in range(1, len(x_m)):
        M[i] = M[i-1] + (V[i-1] + V[i]) * dx / 2.0
    
    return {
        'x_m': x_m,
        'V': V,
        'M': M,
        'RA': RA,
        'RB': RB
    }


def compute_deflection_from_M(
    x_m: np.ndarray,
    M: np.ndarray,
    E: float,
    I: float
) -> Tuple[np.ndarray, float, float]:
    """
    Compute deflection v(x) by numerically integrating curvature.
    
    For a simply-supported beam:
    - v''(x) = M(x) / (E * I)
    - Boundary conditions: v(0) = 0, v(L) = 0
    
    Parameters:
    -----------
    x_m : np.ndarray
        Position array in metres
    M : np.ndarray
        Bending moment array in N·m
    E : float
        Young's modulus in Pa
    I : float
        Second moment of area in m^4
    
    Returns:
    --------
    v : np.ndarray
        Deflection in metres
    C1 : float
        First integration constant
    C2 : float
        Second integration constant
    """
    # Compute curvature
    kappa = M / (E * I)
    
    # First integration: slope θ(x) = ∫κ dx
    dx = x_m[1] - x_m[0]
    theta = np.zeros_like(x_m)
    
    for i in range(1, len(x_m)):
        theta[i] = theta[i-1] + (kappa[i-1] + kappa[i]) * dx / 2.0
    
    # Second integration: v(x) = ∫θ dx
    v_raw = np.zeros_like(x_m)
    
    for i in range(1, len(x_m)):
        v_raw[i] = v_raw[i-1] + (theta[i-1] + theta[i]) * dx / 2.0
    
    # Apply boundary conditions: v(0) = 0, v(L) = 0
    C2 = -v_raw[0]
    L = x_m[-1] - x_m[0]
    C1 = -(v_raw[-1] + C2) / L if L > 0 else 0.0
    
    # Apply corrections
    v = v_raw + C1 * x_m + C2
    
    return v, C1, C2


def apply_load_factors(loads: List, wind_factor: float, barrier_factor: float) -> List:
    """
    Apply partial factors to loads and return new list.
    
    Parameters:
    -----------
    loads : List[Load]
        Base loads from LoadingInputs
    wind_factor : float
        Partial factor for wind load
    barrier_factor : float
        Partial factor for barrier load
    
    Returns:
    --------
    List[Load]
        New list with factored magnitudes
    """
    from copy import deepcopy
    
    factored_loads = []
    for load in loads:
        load_copy = deepcopy(load)
        
        # Apply appropriate factor based on load kind
        if hasattr(load, 'kind'):
            if 'WIND' in str(load.kind).upper():
                load_copy.magnitude *= wind_factor
            elif 'BARRIER' in str(load.kind).upper():
                load_copy.magnitude *= barrier_factor
        
        factored_loads.append(load_copy)
    
    return factored_loads


def analyze_uls_cases(
    geom,
    loading_inputs,
    load_case_set,
    n_points: int = 501
) -> Dict:
    """
    Analyze all ULS load cases to get reactions, shear, and moment.
    NO deflection calculation - we only need M and V for strength checks.
    
    Parameters:
    -----------
    geom : Geometry
        Geometry object with span_mm
    loading_inputs : LoadingInputs
        Loading inputs object
    load_case_set : LoadCaseSet
        Container with ULS and SLS load cases
    n_points : int
        Number of discretization points
    
    Returns:
    --------
    Dict with structure:
    {
        'cases': {
            'case_name_1': {
                'x_m': array,
                'V_N': array,
                'M_Nm': array,
                'RA_N': float,
                'RB_N': float,
                'M_max_Nm': float,
                'V_max_N': float
            },
            ...
        },
        'governing': {
            'M_max': ('case_name', value),
            'V_max': ('case_name', value),
            'case_M': 'case_name',
            'case_V': 'case_name'
        }
    }
    """
    base_loads = loading_inputs.to_loads()
    
    results = {
        'cases': {},
        'governing': {}
    }
    
    M_max_overall = 0.0
    M_max_case = None
    V_max_overall = 0.0
    V_max_case = None
    
    for case in load_case_set.uls_cases:
        # Apply load factors
        factored_loads = apply_load_factors(
            base_loads,
            case.wind_factor,
            case.barrier_factor
        )
        
        # Analyze this case
        analysis = compute_wind_barrier_uniform_and_point(
            span_mm=geom.span_mm,
            loads=factored_loads,
            n_points=n_points
        )
        
        # Find max values
        M_abs = np.abs(analysis['M'])
        V_abs = np.abs(analysis['V'])
        
        M_max = np.max(M_abs)
        V_max = np.max(V_abs)
        
        x_Mmax = analysis['x_m'][np.argmax(M_abs)]
        x_Vmax = analysis['x_m'][np.argmax(V_abs)]
        
        # Store case results
        results['cases'][case.name] = {
            'x_m': analysis['x_m'],
            'V_N': analysis['V'],
            'M_Nm': analysis['M'],
            'RA_N': analysis['RA'],
            'RB_N': analysis['RB'],
            'M_max_Nm': M_max,
            'V_max_N': V_max,
            'x_Mmax_m': x_Mmax,
            'x_Vmax_m': x_Vmax
        }
        
        # Track governing
        if M_max > M_max_overall:
            M_max_overall = M_max
            M_max_case = case.name
        
        if V_max > V_max_overall:
            V_max_overall = V_max
            V_max_case = case.name
    
    results['governing'] = {
        'M_max': (M_max_case, M_max_overall),
        'V_max': (V_max_case, V_max_overall),
        'case_M': M_max_case,
        'case_V': V_max_case
    }
    
    return results


def analyze_sls_deflection_requirement(
    geom,
    loading_inputs,
    load_case_set,
    E: float,
    deflection_limit_mm: float,
    n_points: int = 501
) -> Dict:
    """
    Analyze all SLS load cases to determine required second moment of area (I).
    
    Method:
    1. For each SLS case, compute M(x) with factored loads
    2. Compute deflection with I = 1.0 m^4 (unit deflection)
    3. Scale to find required I: I_req = v_unit_max / v_limit
    4. Return the governing I_req across all SLS cases
    
    Parameters:
    -----------
    geom : Geometry
        Geometry object with span_mm
    loading_inputs : LoadingInputs
        Loading inputs object
    load_case_set : LoadCaseSet
        Container with SLS load cases
    E : float
        Young's modulus in Pa
    deflection_limit_mm : float
        Deflection limit in millimeters
    n_points : int
        Number of discretization points
    
    Returns:
    --------
    Dict with structure:
    {
        'cases': {
            'case_name_1': {
                'I_req_m4': float,
                'v_unit_max_m': float (deflection with I=1.0)
            },
            ...
        },
        'governing': {
            'I_req_m4': float (maximum required I),
            'case': 'case_name',
            'v_limit_m': float
        }
    }
    """
    base_loads = loading_inputs.to_loads()
    v_limit_m = deflection_limit_mm / 1000.0  # Convert to metres
    
    results = {
        'cases': {},
        'governing': {}
    }
    
    I_req_max = 0.0
    I_req_case = None
    
    for case in load_case_set.sls_cases:
        # Apply load factors
        factored_loads = apply_load_factors(
            base_loads,
            case.wind_factor,
            case.barrier_factor
        )
        
        # Get moment diagram
        analysis = compute_wind_barrier_uniform_and_point(
            span_mm=geom.span_mm,
            loads=factored_loads,
            n_points=n_points
        )
        
        # Compute deflection with I = 1.0 m^4 (unit deflection)
        I_unit = 1.0
        v_unit, _, _ = compute_deflection_from_M(
            x_m=analysis['x_m'],
            M=analysis['M'],
            E=E,
            I=I_unit
        )
        
        # Find max deflection
        v_unit_max = np.max(np.abs(v_unit))
        
        # Calculate required I to meet deflection limit
        # v_actual = v_unit / I_req
        # v_actual = v_limit
        # => I_req = v_unit / v_limit
        if v_limit_m > 0 and v_unit_max > 0:
            I_req = v_unit_max / v_limit_m
        else:
            I_req = 0.0
        
        # Store case results
        results['cases'][case.name] = {
            'I_req_m4': I_req,
            'v_unit_max_m': v_unit_max
        }
        
        # Track governing (maximum required I)
        if I_req > I_req_max:
            I_req_max = I_req
            I_req_case = case.name
    
    results['governing'] = {
        'I_req_m4': I_req_max,
        'case': I_req_case,
        'v_limit_m': v_limit_m,
        'v_limit_mm': deflection_limit_mm
    }
    
    return results


def compute_required_section_modulus(
    M_max_Nm: float,
    sigma_allow_Pa: float
) -> float:
    """
    Compute required section modulus for bending.
    
    Z_req = M_max / σ_allow
    
    Parameters:
    -----------
    M_max_Nm : float
        Maximum bending moment in N·m
    sigma_allow_Pa : float
        Allowable stress in Pa
    
    Returns:
    --------
    Z_req_m3 : float
        Required section modulus in m^3
    """
    if sigma_allow_Pa <= 0:
        return float('inf')
    
    return M_max_Nm / sigma_allow_Pa
