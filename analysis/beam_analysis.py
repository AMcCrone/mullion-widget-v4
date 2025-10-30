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
from input.loading import LoadingInputs, Load, LoadKind
from beam_analysis import analyze_loadcase

geom = Geometry(span_mm=3000, bay_width_mm=1000)
# Example: wind 0.05 N/mm (=> 50 N/m), barrier 0.74 kN/m total -> as point P_N=0.74 * bay_width_mm
loads = [
   Load(kind=LoadKind.WIND, magnitude=0.05, distribution="uniform"),  # N/mm
   Load(kind=LoadKind.BARRIER, magnitude=814.0, distribution="point", height_mm=1100)  # N
]
E = 69e9  # Pa
I = 8.5e-6  # m^4 (example)
results = analyze_loadcase(geom.span_mm, loads, E, I)
# results contains arrays x_m, V_N, M_Nm, v_m, and scalars M_max_Nm and v_max_m
```

Wiring into Streamlit:
----------------------
Call `analyze_loadcase` for each LoadCase, passing the LoadCase.loads list.
The results dict contains all arrays and scalars needed for plotting and sizing checks.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass


def compute_wind_barrier_uniform_and_point(
    span_mm: float,
    loads: List,  # List[Load] - avoiding import to keep module self-contained
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
    
    Unit Conversions:
    -----------------
    - span: mm -> m (divide by 1000)
    - uniform loads: N/mm -> N/m (multiply by 1000)
    - point loads: already in N
    """
    # Convert span to metres
    L = span_mm / 1000.0  # m
    
    # Create position array
    x_m = np.linspace(0, L, n_points)
    
    # Separate loads into uniform and point
    uniform_loads = []  # List of (w_Npm,) tuples
    point_loads = []    # List of (P_N, a_m) tuples
    
    for load in loads:
        if load.distribution == 'uniform':
            # Convert N/mm to N/m
            w_Npm = load.magnitude * 1000.0
            uniform_loads.append(w_Npm)
        elif load.distribution == 'point':
            # Point load already in N
            P_N = load.magnitude
            # Assume point loads are applied at midspan unless specified
            # For generality, we could add a position attribute to Load
            # For now, assume midspan
            a_m = L / 2.0
            point_loads.append((P_N, a_m))
    
    # Compute reactions using equilibrium
    # Total uniform load resultant
    W_total = sum(w * L for w in uniform_loads)
    
    # Total point loads
    P_total = sum(P for P, a in point_loads)
    
    # Total vertical load
    total_load = W_total + P_total
    
    # Moment equilibrium about left support to find RB
    # For uniform loads: moment arm = L/2
    moment_uniform = sum(w * L * (L / 2.0) for w in uniform_loads)
    
    # For point loads: moment arm = a
    moment_point = sum(P * a for P, a in point_loads)
    
    total_moment = moment_uniform + moment_point
    
    # Solve for reactions
    if L > 0:
        RB = total_moment / L
        RA = total_load - RB
    else:
        RA = RB = 0.0
    
    # Compute shear force V(x)
    # V(x) = RA - sum(w_i * x) - sum(P_j for a_j <= x)
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
    # M(x) = integral from 0 to x of V(s) ds
    # Use cumulative trapezoidal integration
    dx = x_m[1] - x_m[0]  # Assuming uniform spacing
    M = np.zeros_like(x_m)
    M[0] = 0.0
    
    for i in range(1, len(x_m)):
        # Trapezoidal rule: area = (V[i-1] + V[i]) * dx / 2
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
    
    Method:
    1. Compute curvature κ(x) = M(x) / (E * I)
    2. Integrate once: θ(x) = ∫κ dx + C1
    3. Integrate twice: v(x) = ∫θ dx + C2
    4. Apply BCs to solve for C1 and C2
    
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
    # Use cumulative trapezoidal integration
    dx = x_m[1] - x_m[0]  # Assuming uniform spacing
    theta = np.zeros_like(x_m)
    
    for i in range(1, len(x_m)):
        theta[i] = theta[i-1] + (kappa[i-1] + kappa[i]) * dx / 2.0
    
    # Second integration: v(x) = ∫θ dx
    v_raw = np.zeros_like(x_m)
    
    for i in range(1, len(x_m)):
        v_raw[i] = v_raw[i-1] + (theta[i-1] + theta[i]) * dx / 2.0
    
    # Apply boundary conditions: v(0) = 0, v(L) = 0
    # v(x) = v_raw(x) + C1*x + C2
    # BC1: v(0) = v_raw(0) + C2 = 0  =>  C2 = -v_raw(0) = 0 (already satisfied)
    # BC2: v(L) = v_raw(L) + C1*L + C2 = 0  =>  C1 = -(v_raw(L) + C2) / L
    
    C2 = -v_raw[0]
    L = x_m[-1] - x_m[0]
    C1 = -(v_raw[-1] + C2) / L if L > 0 else 0.0
    
    # Apply corrections
    v = v_raw + C1 * x_m + C2
    
    return v, C1, C2


def analyze_loadcase(
    span_mm: float,
    loads: List,
    E: float,
    I: float,
    n_points: int = 501
) -> Dict:
    """
    Perform complete beam analysis for a load case.
    
    Parameters:
    -----------
    span_mm : float
        Span length in millimeters
    loads : List[Load]
        List of Load objects
    E : float
        Young's modulus in Pa
    I : float
        Second moment of area in m^4
    n_points : int
        Number of discretization points (default 501)
    
    Returns:
    --------
    dict with keys:
        - 'x_m': np.ndarray, position in metres
        - 'V_N': np.ndarray, shear force in N
        - 'M_Nm': np.ndarray, bending moment in N·m
        - 'RA_N': float, left reaction in N
        - 'RB_N': float, right reaction in N
        - 'M_max_Nm': float, maximum bending moment magnitude in N·m
        - 'x_Mmax_m': float, location of M_max in m
        - 'V_max_N': float, maximum shear force magnitude in N
        - 'x_Vmax_m': float, location of V_max in m
        - 'v_m': np.ndarray, deflection in metres
        - 'v_max_m': float, maximum deflection magnitude in m
        - 'x_vmax_m': float, location of v_max in m
    """
    # Compute reactions and internal forces
    results = compute_wind_barrier_uniform_and_point(span_mm, loads, n_points)
    
    x_m = results['x_m']
    V = results['V']
    M = results['M']
    RA = results['RA']
    RB = results['RB']
    
    # Find maximum moment
    M_abs = np.abs(M)
    idx_Mmax = np.argmax(M_abs)
    M_max_Nm = M_abs[idx_Mmax]
    x_Mmax_m = x_m[idx_Mmax]
    
    # Find maximum shear
    V_abs = np.abs(V)
    idx_Vmax = np.argmax(V_abs)
    V_max_N = V_abs[idx_Vmax]
    x_Vmax_m = x_m[idx_Vmax]
    
    # Compute deflection
    v, C1, C2 = compute_deflection_from_M(x_m, M, E, I)
    
    # Find maximum deflection (by magnitude)
    v_abs = np.abs(v)
    idx_vmax = np.argmax(v_abs)
    v_max_m = v_abs[idx_vmax]
    x_vmax_m = x_m[idx_vmax]
    
    return {
        'x_m': x_m,
        'V_N': V,
        'M_Nm': M,
        'RA_N': RA,
        'RB_N': RB,
        'M_max_Nm': M_max_Nm,
        'x_Mmax_m': x_Mmax_m,
        'V_max_N': V_max_N,
        'x_Vmax_m': x_Vmax_m,
        'v_m': v,
        'v_max_m': v_max_m,
        'x_vmax_m': x_vmax_m,
        'C1': C1,
        'C2': C2
    }


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


def compute_required_I_for_deflection(
    span_mm: float,
    loads: List,
    E: float,
    v_limit_m: float,
    n_points: int = 501
) -> float:
    """
    Compute required second moment of area to satisfy deflection limit.
    
    Method: Since v ∝ 1/I, we compute deflection with I=1.0 m^4, then scale.
    I_req = v_unit_max / v_limit
    
    Parameters:
    -----------
    span_mm : float
        Span length in millimeters
    loads : List[Load]
        List of Load objects
    E : float
        Young's modulus in Pa
    v_limit_m : float
        Deflection limit in metres
    n_points : int
        Number of discretization points
    
    Returns:
    --------
    I_req_m4 : float
        Required second moment of area in m^4
    """
    if v_limit_m <= 0:
        return float('inf')
    
    # Compute deflection with I = 1.0 m^4
    I_unit = 1.0
    results_unit = analyze_loadcase(span_mm, loads, E, I_unit, n_points)
    v_unit_max = results_unit['v_max_m']
    
    # Scale to find required I
    # v_max_actual = v_unit_max / I_req
    # v_max_actual = v_limit
    # => I_req = v_unit_max / v_limit
    
    if v_unit_max <= 0:
        return 0.0
    
    I_req_m4 = v_unit_max / v_limit_m
    
    return I_req_m4
