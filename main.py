"""
Mullion Sizing Streamlit Application
Comprehensive structural analysis tool for curtain wall mullions
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from pathlib import Path
import sys

# Page configuration
st.set_page_config(
    page_title="Mullion Sizing Tool",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .subsection-header {
        font-size: 1.3rem;
        font-weight: 500;
        color: #34495e;
        margin-top: 1rem;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Import calculation functions
def calculate_deflection_limit(L):
    """Calculate deflection limit based on mullion length"""
    if L <= 3000:
        return L / 200
    elif L < 7500:
        return 5 + L / 300
    else:
        return L / 250

def calculate_ULS_requirements(load_cases, L, bay, wind_pressure, barrier_load, barrier_height, fyd):
    """Calculate required section modulus for each ULS load case"""
    p = wind_pressure * 0.001  # Convert kPa to N/mm²
    w = p * bay  # N/mm
    M_WL = (w * L**2) / 8  # Nmm
    M_BL = ((barrier_load * bay) * barrier_height) / 2  # Nmm
    
    results = {}
    for case_name, factors in load_cases.items():
        wind_factor, barrier_factor = factors
        M_ULS = wind_factor * M_WL + barrier_factor * M_BL
        Z_req = M_ULS / fyd  # mm³
        Z_req_cm3 = Z_req / 1000  # cm³
        results[case_name] = {
            'M_ULS_kNm': M_ULS / 1e6,
            'Z_req_cm3': Z_req_cm3,
            'wind_factor': wind_factor,
            'barrier_factor': barrier_factor
        }
    
    max_case = max(results.items(), key=lambda x: x[1]['Z_req_cm3'])
    return results, max_case[0], max_case[1]['Z_req_cm3']

def calculate_SLS_requirements(load_cases, L, bay, wind_pressure, barrier_load, barrier_height, E, defl_limit):
    """Calculate required moment of inertia for each SLS load case"""
    p = wind_pressure * 0.001  # Convert kPa to N/mm²
    w = p * bay  # N/mm
    F_BL = barrier_load * bay  # N
    
    results = {}
    for case_name, factors in load_cases.items():
        wind_factor, barrier_factor = factors
        w_eff = wind_factor * w
        F_BL_eff = barrier_factor * F_BL
        
        if w_eff > 0 and F_BL_eff == 0:
            I_req = (5 * w_eff * L**4) / (384 * E * defl_limit)
        elif w_eff == 0 and F_BL_eff > 0:
            I_req = ((F_BL_eff * barrier_height) / (12 * E * defl_limit)) * (0.75 * L**2 - barrier_height**2)
        elif w_eff > 0 and F_BL_eff > 0:
            num = (5 * w_eff * L**4 + 32 * F_BL_eff * barrier_height * (0.75 * L**2 - barrier_height**2))
            den = 384 * E * defl_limit
            I_req = num / den
        else:
            I_req = 0
        
        I_req_cm4 = I_req / 10000
        results[case_name] = {
            'I_req_cm4': I_req_cm4,
            'wind_factor': wind_factor,
            'barrier_factor': barrier_factor
        }
    
    max_case = max(results.items(), key=lambda x: x[1]['I_req_cm4'])
    return results, max_case[0], max_case[1]['I_req_cm4']

# Initialize session state
if 'uls_cases' not in st.session_state:
    st.session_state.uls_cases = pd.DataFrame({
        'Load Case': ['ULS 1: 1.5W + 0.75L', 'ULS 2: 0.75W + 1.5L', 'ULS 3: 1.5W', 'ULS 4: 1.5L'],
        'Wind Factor': [1.5, 0.75, 1.5, 0.0],
        'Barrier Factor': [0.75, 1.5, 0.0, 1.5]
    })

if 'sls_cases' not in st.session_state:
    st.session_state.sls_cases = pd.DataFrame({
        'Load Case': ['SLS 1: W', 'SLS 2: L'],
        'Wind Factor': [1.0, 0.0],
        'Barrier Factor': [0.0, 1.0]
    })

# Header
st.markdown('<p class="main-header">🏗️ Mullion Sizing Tool</p>', unsafe_allow_html=True)
st.markdown("**Comprehensive structural analysis for curtain wall mullions**")

# Sidebar for navigation
with st.sidebar:
    st.markdown("### Navigation")
    section = st.radio(
        "Go to section:",
        ["📐 Geometry", "⚖️ Loading", "🔧 Material Properties", "📊 Load Cases", "🔬 Analysis Results", "📦 Section Selection"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.info("This tool performs structural analysis of curtain wall mullions according to Eurocode principles.")

# ============================================================================
# SECTION 1: GEOMETRY
# ============================================================================
if section == "📐 Geometry":
    st.markdown('<p class="section-header">📐 Geometry Definition</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<p class="subsection-header">Dimensions</p>', unsafe_allow_html=True)
        mullion_length = st.number_input(
            "Mullion Length (mm)",
            min_value=500.0,
            max_value=15000.0,
            value=4000.0,
            step=100.0,
            help="Clear span length of the mullion"
        )
        
        bay_width = st.number_input(
            "Bay Width (mm)",
            min_value=500.0,
            max_value=5000.0,
            value=3000.0,
            step=100.0,
            help="Tributary width for load calculation"
        )
        
        # Store in session state
        st.session_state.mullion_length = mullion_length
        st.session_state.bay_width = bay_width
        
        # Calculate derived values
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown(f"""
        **Derived Values:**
        - Mullion Length: {mullion_length/1000:.3f} m
        - Bay Width: {bay_width/1000:.3f} m
        - Tributary Area: {(mullion_length * bay_width) / 1e6:.2f} m²
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<p class="subsection-header">Geometry Visualization</p>', unsafe_allow_html=True)
        
        # Create geometry diagram
        fig = go.Figure()
        
        # Mullion (vertical)
        fig.add_trace(go.Scatter(
            x=[0, 0],
            y=[0, mullion_length],
            mode='lines',
            line=dict(color='#1f77b4', width=8),
            name='Mullion',
            showlegend=False
        ))
        
        # Support symbols
        support_size = mullion_length * 0.05
        fig.add_trace(go.Scatter(
            x=[-support_size, 0, support_size],
            y=[0, 0, 0],
            mode='lines',
            fill='toself',
            fillcolor='#666',
            line=dict(color='#666', width=2),
            name='Support',
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=[-support_size, 0, support_size],
            y=[mullion_length, mullion_length, mullion_length],
            mode='lines',
            fill='toself',
            fillcolor='#666',
            line=dict(color='#666', width=2),
            showlegend=False
        ))
        
        # Bay width annotation
        fig.add_trace(go.Scatter(
            x=[0, bay_width],
            y=[mullion_length/2, mullion_length/2],
            mode='lines+markers',
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            marker=dict(size=8, symbol='arrow-bar-right'),
            name='Bay Width',
            showlegend=False
        ))
        
        # Annotations
        fig.add_annotation(
            x=bay_width/2,
            y=mullion_length/2 + mullion_length*0.1,
            text=f"Bay Width<br>{bay_width:.0f} mm",
            showarrow=False,
            font=dict(size=12, color='#ff7f0e')
        )
        
        fig.add_annotation(
            x=-bay_width*0.15,
            y=mullion_length/2,
            text=f"Length<br>{mullion_length:.0f} mm",
            showarrow=False,
            font=dict(size=12, color='#1f77b4'),
            textangle=-90
        )
        
        fig.update_layout(
            height=500,
            showlegend=False,
            xaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                range=[-bay_width*0.3, bay_width*1.2]
            ),
            yaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                scaleanchor="x",
                scaleratio=1
            ),
            plot_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# SECTION 2: LOADING
# ============================================================================
elif section == "⚖️ Loading":
    st.markdown('<p class="section-header">⚖️ Loading Definition</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<p class="subsection-header">Load Values</p>', unsafe_allow_html=True)
        
        wind_pressure = st.number_input(
            "Wind Pressure (kPa)",
            min_value=0.0,
            max_value=10.0,
            value=1.0,
            step=0.1,
            help="Design wind pressure on facade"
        )
        
        barrier_load = st.number_input(
            "Barrier Load (kN/m)",
            min_value=0.0,
            max_value=5.0,
            value=0.74,
            step=0.01,
            help="Horizontal line load from balustrade/barrier"
        )
        
        barrier_height = st.number_input(
            "Barrier Height (mm)",
            min_value=0.0,
            max_value=2000.0,
            value=1100.0,
            step=50.0,
            help="Height above mullion base where barrier load acts"
        )
        
        # Store in session state
        st.session_state.wind_pressure = wind_pressure
        st.session_state.barrier_load = barrier_load
        st.session_state.barrier_height = barrier_height
        
        # Calculate derived loads
        if 'bay_width' in st.session_state and 'mullion_length' in st.session_state:
            wind_udl = wind_pressure * st.session_state.bay_width / 1000
            barrier_pl = barrier_load * st.session_state.bay_width
            
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown(f"""
            **Load Summary:**
            - Wind UDL: {wind_udl:.2f} N/mm
            - Barrier Point Load: {barrier_pl:.0f} N
            - Barrier Height: {barrier_height/1000:.3f} m
            """)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<p class="subsection-header">Loading Diagram</p>', unsafe_allow_html=True)
        
        if 'mullion_length' in st.session_state:
            L = st.session_state.mullion_length
            
            fig = go.Figure()
            
            # Mullion
            fig.add_trace(go.Scatter(
                x=[0, 0],
                y=[0, L],
                mode='lines',
                line=dict(color='#1f77b4', width=8),
                showlegend=False
            ))
            
            # Wind load arrows
            num_arrows = 8
            for i in range(num_arrows + 1):
                y_pos = i * L / num_arrows
                arrow_len = L * 0.15
                fig.add_annotation(
                    x=0,
                    y=y_pos,
                    ax=arrow_len,
                    ay=0,
                    xref='x',
                    yref='y',
                    axref='x',
                    ayref='y',
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor='#2ca02c'
                )
            
            # Barrier load
            if barrier_load > 0:
                arrow_len = L * 0.25
                fig.add_annotation(
                    x=0,
                    y=barrier_height,
                    ax=arrow_len,
                    ay=0,
                    xref='x',
                    yref='y',
                    axref='x',
                    ayref='y',
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1.5,
                    arrowwidth=3,
                    arrowcolor='#d62728'
                )
                
                fig.add_annotation(
                    x=arrow_len * 0.6,
                    y=barrier_height,
                    text=f"Barrier Load<br>{barrier_load} kN/m",
                    showarrow=False,
                    font=dict(size=11, color='#d62728')
                )
            
            # Wind annotation
            fig.add_annotation(
                x=L * 0.1,
                y=L * 0.9,
                text=f"Wind<br>{wind_pressure} kPa",
                showarrow=False,
                font=dict(size=11, color='#2ca02c')
            )
            
            # Supports
            support_size = L * 0.05
            for y_pos in [0, L]:
                fig.add_trace(go.Scatter(
                    x=[-support_size, 0, support_size],
                    y=[y_pos, y_pos, y_pos],
                    mode='lines',
                    fill='toself',
                    fillcolor='#666',
                    line=dict(color='#666', width=2),
                    showlegend=False
                ))
            
            fig.update_layout(
                height=500,
                showlegend=False,
                xaxis=dict(
                    showgrid=False,
                    showticklabels=False,
                    zeroline=False,
                    range=[-L*0.1, L*0.35]
                ),
                yaxis=dict(
                    showgrid=False,
                    showticklabels=False,
                    zeroline=False,
                    scaleanchor="x",
                    scaleratio=1
                ),
                plot_bgcolor='white',
                margin=dict(l=20, r=20, t=20, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# SECTION 3: MATERIAL PROPERTIES
# ============================================================================
elif section == "🔧 Material Properties":
    st.markdown('<p class="section-header">🔧 Material Properties</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<p class="subsection-header">Material Parameters</p>', unsafe_allow_html=True)
        
        fy = st.number_input(
            "Yield Strength, fy (MPa)",
            min_value=100.0,
            max_value=500.0,
            value=160.0,
            step=10.0,
            help="Characteristic yield strength of material"
        )
        
        E = st.number_input(
            "Young's Modulus, E (MPa)",
            min_value=50000.0,
            max_value=210000.0,
            value=70000.0,
            step=1000.0,
            help="Modulus of elasticity"
        )
        
        gamma_M1 = st.number_input(
            "Partial Safety Factor, γM1",
            min_value=1.0,
            max_value=1.5,
            value=1.1,
            step=0.05,
            help="Material partial safety factor for resistance"
        )
        
        # Calculate design strength
        fyd = fy / gamma_M1
        
        # Store in session state
        st.session_state.fy = fy
        st.session_state.E = E
        st.session_state.gamma_M1 = gamma_M1
        st.session_state.fyd = fyd
        
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown(f"""
        **Design Strength:**
        
        fyd = fy / γM1 = {fy:.0f} / {gamma_M1:.2f} = **{fyd:.1f} MPa**
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<p class="subsection-header">Material Information</p>', unsafe_allow_html=True)
        
        st.info("""
        **Typical Values:**
        
        **Aluminium Alloys:**
        - 6060-T5: fy = 160 MPa, E = 70,000 MPa
        - 6063-T6: fy = 215 MPa, E = 70,000 MPa
        - 6082-T6: fy = 260 MPa, E = 70,000 MPa
        
        **Steel:**
        - S235: fy = 235 MPa, E = 210,000 MPa
        - S275: fy = 275 MPa, E = 210,000 MPa
        - S355: fy = 355 MPa, E = 210,000 MPa
        
        **Partial Safety Factors (EN 1993-1-1):**
        - γM1 = 1.1 (Aluminium typical)
        - γM0 = 1.0 (Steel typical)
        """)

# ============================================================================
# SECTION 4: LOAD CASES
# ============================================================================
elif section == "📊 Load Cases":
    st.markdown('<p class="section-header">📊 Load Case Definition</p>', unsafe_allow_html=True)
    
    st.markdown("""
    Define the load combinations for Ultimate Limit State (ULS) and Serviceability Limit State (SLS) analyses.
    Load factors are applied to wind and barrier loads.
    """)
    
    # ULS Load Cases
    st.markdown('<p class="subsection-header">Ultimate Limit State (ULS) Load Cases</p>', unsafe_allow_html=True)
    
    st.markdown("Edit the table below to add, remove, or modify ULS load cases:")
    
    edited_uls = st.data_editor(
        st.session_state.uls_cases,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Load Case": st.column_config.TextColumn("Load Case", help="Description of load case"),
            "Wind Factor": st.column_config.NumberColumn("Wind Factor (γW)", min_value=0.0, max_value=2.0, step=0.05),
            "Barrier Factor": st.column_config.NumberColumn("Barrier Factor (γB)", min_value=0.0, max_value=2.0, step=0.05)
        }
    )
    
    st.session_state.uls_cases = edited_uls
    
    st.markdown("---")
    
    # SLS Load Cases
    st.markdown('<p class="subsection-header">Serviceability Limit State (SLS) Load Cases</p>', unsafe_allow_html=True)
    
    st.markdown("Edit the table below to add, remove, or modify SLS load cases:")
    
    edited_sls = st.data_editor(
        st.session_state.sls_cases,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Load Case": st.column_config.TextColumn("Load Case", help="Description of load case"),
            "Wind Factor": st.column_config.NumberColumn("Wind Factor (γW)", min_value=0.0, max_value=1.5, step=0.05),
            "Barrier Factor": st.column_config.NumberColumn("Barrier Factor (γB)", min_value=0.0, max_value=1.5, step=0.05)
        }
    )
    
    st.session_state.sls_cases = edited_sls
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Reset to EN 1990 Defaults", type="secondary"):
            st.session_state.uls_cases = pd.DataFrame({
                'Load Case': ['ULS 1: 1.5W + 0.75L', 'ULS 2: 0.75W + 1.5L', 'ULS 3: 1.5W', 'ULS 4: 1.5L'],
                'Wind Factor': [1.5, 0.75, 1.5, 0.0],
                'Barrier Factor': [0.75, 1.5, 0.0, 1.5]
            })
            st.session_state.sls_cases = pd.DataFrame({
                'Load Case': ['SLS 1: W', 'SLS 2: L'],
                'Wind Factor': [1.0, 0.0],
                'Barrier Factor': [0.0, 1.0]
            })
            st.rerun()

# ============================================================================
# SECTION 5: ANALYSIS RESULTS
# ============================================================================
elif section == "🔬 Analysis Results":
    st.markdown('<p class="section-header">🔬 Analysis Results</p>', unsafe_allow_html=True)
    
    # Check if all required inputs are available
    required_params = ['mullion_length', 'bay_width', 'wind_pressure', 'barrier_load', 
                       'barrier_height', 'fyd', 'E']
    
    if all(param in st.session_state for param in required_params):
        
        # Extract parameters
        L = st.session_state.mullion_length
        bay = st.session_state.bay_width
        wind = st.session_state.wind_pressure
        barrier = st.session_state.barrier_load
        barrier_h = st.session_state.barrier_height
        fyd = st.session_state.fyd
        E = st.session_state.E
        
        # Calculate deflection limit
        defl_limit = calculate_deflection_limit(L)
        
        # Convert DataFrames to dictionaries for calculations
        uls_dict = {row['Load Case']: (row['Wind Factor'], row['Barrier Factor']) 
                    for _, row in st.session_state.uls_cases.iterrows()}
        sls_dict = {row['Load Case']: (row['Wind Factor'], row['Barrier Factor']) 
                    for _, row in st.session_state.sls_cases.iterrows()}
        
        # Run ULS analysis
        uls_results, uls_max_case, uls_max_z = calculate_ULS_requirements(
            uls_dict, L, bay, wind, barrier, barrier_h, fyd
        )
        
        # Run SLS analysis
        sls_results, sls_max_case, sls_max_i = calculate_SLS_requirements(
            sls_dict, L, bay, wind, barrier, barrier_h, E, defl_limit
        )
        
        # Store results in session state
        st.session_state.uls_results = uls_results
        st.session_state.sls_results = sls_results
        st.session_state.uls_max_case = uls_max_case
        st.session_state.uls_max_z = uls_max_z
        st.session_state.sls_max_case = sls_max_case
        st.session_state.sls_max_i = sls_max_i
        st.session_state.defl_limit = defl_limit
        
        # Display summary
        st.markdown('<p class="subsection-header">Design Summary</p>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Deflection Limit", f"{defl_limit:.2f} mm", 
                     help=f"Based on L = {L:.0f} mm")
        
        with col2:
            st.metric("ULS Governing Case", uls_max_case)
            st.metric("Required Z", f"{uls_max_z:.2f} cm³")
        
        with col3:
            st.metric("SLS Governing Case", sls_max_case)
            st.metric("Required I", f"{sls_max_i:.2f} cm⁴")
        
        st.markdown("---")
        
        # ULS Results Table
        st.markdown('<p class="subsection-header">ULS Analysis Results</p>', unsafe_allow_html=True)
        
        uls_df = pd.DataFrame([
            {
                'Load Case': case,
                'γW': data['wind_factor'],
                'γB': data['barrier_factor'],
                'MULS (kNm)': data['M_ULS_kNm'],
                'Zreq (cm³)': data['Z_req_cm3'],
                'Status': '✓ Governs' if case == uls_max_case else ''
            }
            for case, data in uls_results.items()
        ])
        
        st.dataframe(
            uls_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "MULS (kNm)": st.column_config.NumberColumn(format="%.2f"),
                "Zreq (cm³)": st.column_config.NumberColumn(format="%.2f")
            }
        )
        
        # SLS Results Table
        st.markdown('<p class="subsection-header">SLS Analysis Results</p>', unsafe_allow_html=True)
        
        sls_df = pd.DataFrame([
            {
                'Load Case': case,
                'γW': data['wind_factor'],
                'γB': data['barrier_factor'],
                'Ireq (cm⁴)': data['I_req_cm4'],
                'Status': '✓ Governs' if case == sls_max_case else ''
            }
            for case, data in sls_results.items()
        ])
        
        st.dataframe(
            sls_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ireq (cm⁴)": st.column_config.NumberColumn(format="%.2f")
            }
        )
        
        # Comparison charts
        st.markdown('<p class="subsection-header">Results Comparison</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # ULS chart
            fig_uls = go.Figure()
            fig_uls.add_trace(go.Bar(
                x=list(uls_results.keys()),
                y=[data['Z_req_cm3'] for data in uls_results.values()],
                marker_color=['#d62728' if case == uls_max_case else '#1f77b4' 
                             for case in uls_results.keys()],
                text=[f"{data['Z_req_cm3']:.2f}" for data in uls_results.values()],
                textposition='outside'
            ))
            fig_uls.update_layout(
                title="ULS Required Section Modulus",
                xaxis_title="Load Case",
                yaxis_title="Z required (cm³)",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_uls, use_container_width=True)
        
        with col2:
            # SLS chart
            fig_sls = go.Figure()
            fig_sls.add_trace(go.Bar(
                x=list(sls_results.keys()),
                y=[data['I_req_cm4'] for data in sls_results.values()],
                marker_color=['#d62728' if case == sls_max_case else '#2ca02c' 
                             for case in sls_results.keys()],
                text=[f"{data['I_req_cm4']:.2f}" for data in sls_results.values()],
                textposition='outside'
            ))
            fig_sls.update_layout(
                title="SLS Required Moment of Inertia",
                xaxis_title="Load Case",
                yaxis_title="I required (cm⁴)",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_sls, use_container_width=True)
        
    else:
        st.warning("⚠️ Please complete all input sections before running analysis:")
        missing = []
        if 'mullion_length' not in st.session_state:
            missing.append("- Geometry (Mullion Length & Bay Width)")
        if 'wind_pressure' not in st.session_state:
            missing.append("- Loading (Wind Pressure, Barrier Load & Height)")
        if 'fyd' not in st.session_state:
            missing.append("- Material Properties")
        
        for item in missing:
            st.write(item)

# ============================================================================
# SECTION 6: SECTION SELECTION
# ============================================================================
elif section == "📦 Section Selection":
    st.markdown('<p class="section-header">📦 Section Selection & Verification</p>', unsafe_allow_html=True)
    
    # Check if analysis has been run
    if 'uls_max_z' in st.session_state and 'sls_max_i' in st.session_state:
        
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown(f"""
        **Design Requirements:**
        - Required Section Modulus (ULS): **{st.session_state.uls_max_z:.2f} cm³**
        - Required Moment of Inertia (SLS): **{st.session_state.sls_max_i:.2f} cm⁴**
        - Deflection Limit: **{st.session_state.defl_limit:.2f} mm**
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<p class="subsection-header">Section Database</p>', unsafe_allow_html=True)
        
        # Sample section database (you can replace this with your actual database)
        # Format: Name, Z (cm³), I (cm⁴), Material, Weight (kg/m)
        sections_data = {
            'Section': [
                'RHS 100x50x3', 'RHS 100x50x4', 'RHS 120x60x3', 'RHS 120x60x4',
                'RHS 150x50x3', 'RHS 150x50x4', 'RHS 150x50x5',
                'I-Section 100x50', 'I-Section 120x60', 'I-Section 150x75',
                'Custom Box 80x40x3', 'Custom Box 100x50x4', 'Custom Box 120x60x5'
            ],
            'Z (cm³)': [
                24.5, 31.2, 35.8, 45.6, 42.3, 54.8, 66.2,
                38.5, 52.3, 78.4, 18.7, 36.4, 62.8
            ],
            'I (cm⁴)': [
                122, 156, 215, 274, 318, 411, 496,
                193, 314, 588, 75, 182, 377
            ],
            'Material': [
                'Aluminium', 'Aluminium', 'Aluminium', 'Aluminium',
                'Aluminium', 'Aluminium', 'Aluminium',
                'Steel', 'Steel', 'Steel',
                'Aluminium', 'Aluminium', 'Aluminium'
            ],
            'Weight (kg/m)': [
                1.32, 1.71, 1.58, 2.05, 1.76, 2.28, 2.78,
                8.34, 11.2, 16.8, 0.98, 1.85, 3.24
            ]
        }
        
        sections_df = pd.DataFrame(sections_data)
        
        # Calculate utilization
        sections_df['ULS Utilization (%)'] = (st.session_state.uls_max_z / sections_df['Z (cm³)']) * 100
        sections_df['SLS Utilization (%)'] = (st.session_state.sls_max_i / sections_df['I (cm⁴)']) * 100
        sections_df['Max Utilization (%)'] = sections_df[['ULS Utilization (%)', 'SLS Utilization (%)']].max(axis=1)
        
        # Determine pass/fail
        sections_df['Status'] = sections_df.apply(
            lambda row: '✓ PASS' if row['Z (cm³)'] >= st.session_state.uls_max_z 
                        and row['I (cm⁴)'] >= st.session_state.sls_max_i 
                        else '✗ FAIL',
            axis=1
        )
        
        # Store in session state
        st.session_state.sections_df = sections_df
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            material_filter = st.multiselect(
                "Filter by Material",
                options=sections_df['Material'].unique(),
                default=sections_df['Material'].unique()
            )
        
        with col2:
            status_filter = st.multiselect(
                "Filter by Status",
                options=['✓ PASS', '✗ FAIL'],
                default=['✓ PASS', '✗ FAIL']
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                options=['Max Utilization (%)', 'Weight (kg/m)', 'Section']
            )
        
        # Apply filters
        filtered_df = sections_df[
            (sections_df['Material'].isin(material_filter)) &
            (sections_df['Status'].isin(status_filter))
        ].sort_values(by=sort_by)
        
        # Display table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Z (cm³)": st.column_config.NumberColumn(format="%.2f"),
                "I (cm⁴)": st.column_config.NumberColumn(format="%.2f"),
                "Weight (kg/m)": st.column_config.NumberColumn(format="%.2f"),
                "ULS Utilization (%)": st.column_config.NumberColumn(format="%.1f"),
                "SLS Utilization (%)": st.column_config.NumberColumn(format="%.1f"),
                "Max Utilization (%)": st.column_config.NumberColumn(
                    format="%.1f",
                    help="Maximum of ULS and SLS utilization"
                )
            }
        )
        
        st.markdown("---")
        
        # Section selection for detailed view
        st.markdown('<p class="subsection-header">Detailed Section Analysis</p>', unsafe_allow_html=True)
        
        passing_sections = filtered_df[filtered_df['Status'] == '✓ PASS']['Section'].tolist()
        
        if passing_sections:
            selected_section = st.selectbox(
                "Select a section for detailed analysis",
                options=passing_sections
            )
            
            if selected_section:
                section_data = sections_df[sections_df['Section'] == selected_section].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.markdown(f"""
                    **Section: {selected_section}**
                    
                    **Properties:**
                    - Section Modulus: {section_data['Z (cm³)']:.2f} cm³
                    - Moment of Inertia: {section_data['I (cm⁴)']:.2f} cm⁴
                    - Material: {section_data['Material']}
                    - Weight: {section_data['Weight (kg/m)']:.2f} kg/m
                    
                    **Utilization:**
                    - ULS: {section_data['ULS Utilization (%)']:.1f}%
                    - SLS: {section_data['SLS Utilization (%)']:.1f}%
                    - Maximum: {section_data['Max Utilization (%)']:.1f}%
                    """)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Capacity ratios
                    st.markdown("**Capacity Ratios:**")
                    z_ratio = section_data['Z (cm³)'] / st.session_state.uls_max_z
                    i_ratio = section_data['I (cm⁴)'] / st.session_state.sls_max_i
                    
                    st.write(f"Z provided / Z required = {z_ratio:.2f}")
                    st.write(f"I provided / I required = {i_ratio:.2f}")
                
                with col2:
                    # Utilization chart
                    fig = go.Figure()
                    
                    categories = ['ULS Check', 'SLS Check']
                    utilizations = [
                        section_data['ULS Utilization (%)'],
                        section_data['SLS Utilization (%)']
                    ]
                    colors = ['#1f77b4', '#2ca02c']
                    
                    fig.add_trace(go.Bar(
                        x=categories,
                        y=utilizations,
                        marker_color=colors,
                        text=[f"{u:.1f}%" for u in utilizations],
                        textposition='outside'
                    ))
                    
                    # Add 100% reference line
                    fig.add_hline(
                        y=100,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="100% (Limit)",
                        annotation_position="right"
                    )
                    
                    # Add 80% reference line
                    fig.add_hline(
                        y=80,
                        line_dash="dot",
                        line_color="orange",
                        annotation_text="80% (Efficient)",
                        annotation_position="right"
                    )
                    
                    fig.update_layout(
                        title=f"Utilization: {selected_section}",
                        yaxis_title="Utilization (%)",
                        height=400,
                        showlegend=False,
                        yaxis_range=[0, max(utilizations) * 1.2]
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Performance summary
                if section_data['Max Utilization (%)'] < 80:
                    st.success(f"✓ {selected_section} is well within capacity (max {section_data['Max Utilization (%)']:.1f}% utilization)")
                elif section_data['Max Utilization (%)'] < 100:
                    st.info(f"✓ {selected_section} passes but is near capacity ({section_data['Max Utilization (%)']:.1f}% utilization)")
                else:
                    st.error(f"✗ {selected_section} exceeds capacity ({section_data['Max Utilization (%)']:.1f}% utilization)")
        else:
            st.warning("No sections pass the design requirements with current filters.")
        
        # Comparison of all passing sections
        if len(passing_sections) > 1:
            st.markdown("---")
            st.markdown('<p class="subsection-header">Comparison of Passing Sections</p>', unsafe_allow_html=True)
            
            passing_df = sections_df[sections_df['Section'].isin(passing_sections)]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=passing_df['Max Utilization (%)'],
                y=passing_df['Weight (kg/m)'],
                mode='markers+text',
                marker=dict(
                    size=15,
                    color=passing_df['Max Utilization (%)'],
                    colorscale='RdYlGn_r',
                    showscale=True,
                    colorbar=dict(title="Utilization (%)")
                ),
                text=passing_df['Section'],
                textposition="top center",
                hovertemplate='<b>%{text}</b><br>' +
                             'Utilization: %{x:.1f}%<br>' +
                             'Weight: %{y:.2f} kg/m<br>' +
                             '<extra></extra>'
            ))
            
            fig.update_layout(
                title="Weight vs Utilization (Passing Sections)",
                xaxis_title="Maximum Utilization (%)",
                yaxis_title="Weight (kg/m)",
                height=500,
                showlegend=False,
                hovermode='closest'
            )
            
            # Add reference lines
            fig.add_vline(x=80, line_dash="dot", line_color="orange", 
                         annotation_text="80% Efficient")
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 **Tip:** The optimal section typically has 70-90% utilization for efficiency while maintaining adequate safety margin.")
    
    else:
        st.warning("⚠️ Please run the analysis first (go to 'Analysis Results' section)")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>Mullion Sizing Tool v4.0 | Based on Eurocode Principles</p>
        <p style='font-size: 0.9em;'>⚠️ For preliminary design only. Final designs should be verified by a qualified engineer.</p>
    </div>
""", unsafe_allow_html=True)
