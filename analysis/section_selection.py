"""
Section selection and visualization module for mullion sizing.
Generates ULS, SLS, and 3D utilisation plots against section database.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Tuple, List, Optional
from pathlib import Path


# Color scheme (matching your TikZ theme)
TT_LightBlue = 'rgba(136,219,223, 0.3)'
TT_MidBlue = 'rgb(0,163,173)'
TT_DarkBlue = 'rgb(0,48,60)'
TT_Orange = 'rgb(211,69,29)'
TT_Grey = 'rgb(99,102,105)'


def load_section_database(material: str, excel_path: str = "data/mullion_profile_db.xlsx") -> pd.DataFrame:
    """
    Load section database from Excel file - CACHED VERSION.
    
    Parameters
    ----------
    material : str
        Material type ("Aluminium" or "Steel")
    excel_path : str
        Path to Excel database file
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: SUPPLIER, NAME, MATERIAL, REINF, D, I, Z
    """
    try:
        import streamlit as st
    except:
        st = None
    
    # Determine sheet name based on material
    sheet_name = "aluminium" if material.lower() == "aluminium" else "steel"
    
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine="openpyxl")
    except Exception as e:
        if st:
            st.error(f"Error reading Excel file: {e}")
        raise
    
    # Use columns EXACTLY as they are in Excel - NO MAPPING
    required_cols = ['SUPPLIER', 'NAME', 'MATERIAL', 'REINF', 'D', 'I', 'Z']
    
    # Check if all required columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in Excel file: {missing_cols}")
    
    df = df[required_cols].copy()
    
    # Convert numeric columns
    df['D'] = pd.to_numeric(df['D'], errors='coerce')
    df['I'] = pd.to_numeric(df['I'], errors='coerce')
    df['Z'] = pd.to_numeric(df['Z'], errors='coerce')
    df['REINF'] = df['REINF'].astype(bool)
    
    # Remove any rows with NaN in critical columns
    df = df.dropna(subset=['D', 'I', 'Z'])
    
    return df


def filter_section_database(
    df: pd.DataFrame,
    selected_suppliers: List[str],
    include_reinforced: bool = True,
    include_unreinforced: bool = True
) -> pd.DataFrame:
    """
    Filter section database based on user selections.
    
    Parameters
    ----------
    df : pd.DataFrame
        Section database
    selected_suppliers : List[str]
        List of selected supplier names
    include_reinforced : bool
        Include reinforced sections
    include_unreinforced : bool
        Include unreinforced sections
        
    Returns
    -------
    pd.DataFrame
        Filtered database
    """
    df_filtered = df[df['SUPPLIER'].isin(selected_suppliers)].copy()
    
    # Filter by reinforcement
    reinf_mask = []
    if include_reinforced:
        reinf_mask.append(df_filtered['REINF'] == True)
    if include_unreinforced:
        reinf_mask.append(df_filtered['REINF'] == False)
    
    if reinf_mask:
        df_filtered = df_filtered[np.logical_or.reduce(reinf_mask)]
    
    return df_filtered


def generate_uls_plot(
    df: pd.DataFrame,
    Z_req_cm3: float,
    material: str,
    uls_case_name: str,
    geometry_info: Dict
) -> go.Figure:
    """
    Generate ULS plot showing section modulus vs depth.
    
    Parameters
    ----------
    df : pd.DataFrame
        Filtered section database
    Z_req_cm3 : float
        Required section modulus (cm³)
    material : str
        Material type
    uls_case_name : str
        Name of governing ULS case
    geometry_info : Dict
        Dictionary with geometry parameters for title
        
    Returns
    -------
    go.Figure
        Plotly figure
    """
    depths = df['D'].values
    Z_available = df['Z'].values  # Already in cm³
    reinf = df['REINF'].values
    profiles = df['NAME'].values
    suppliers = df['SUPPLIER'].values
    
    # Determine pass/fail
    uls_passed = Z_available >= Z_req_cm3
    
    # Colors and symbols
    uls_colors = ['seagreen' if p else 'darkred' for p in uls_passed]
    uls_symbols = ['square' if r else 'circle' for r in reinf]
    
    # Hover text
    uls_hover = [
        f"{profiles[i]}<br>Supplier: {suppliers[i]}<br>"
        f"Depth: {depths[i]:.0f} mm<br>"
        f"Z: {Z_available[i]:.2f} cm³<br>"
        f"ULS: {'Pass' if uls_passed[i] else 'Fail'}"
        for i in range(len(depths))
    ]
    
    # Plot range
    x_min = np.min(depths) * 0.95 if len(depths) > 0 else 0
    x_max = np.max(depths) * 1.05 if len(depths) > 0 else 100
    y_max = 4 * Z_req_cm3
    
    # Create figure
    fig = go.Figure()
    
    # Pass region (above requirement)
    fig.add_shape(
        type="rect",
        x0=x_min, x1=x_max,
        y0=Z_req_cm3, y1=y_max,
        fillcolor=TT_LightBlue,
        opacity=0.2,
        line_width=0,
        layer='below'
    )
    
    # Fail region (below requirement)
    fig.add_shape(
        type="rect",
        x0=x_min, x1=x_max,
        y0=0, y1=Z_req_cm3,
        fillcolor=TT_MidBlue,
        opacity=0.2,
        line_width=0,
        layer='below'
    )
    
    # Scatter plot
    fig.add_trace(go.Scatter(
        x=depths,
        y=Z_available,
        mode='markers',
        marker=dict(
            color=uls_colors,
            symbol=uls_symbols,
            size=15,
            line=dict(color='black', width=1)
        ),
        text=uls_hover,
        hoverinfo='text',
        showlegend=False
    ))
    
    # Layout
    title_text = (
        f"{material} ULS Design ({uls_case_name})<br>"
        f"<sub>Span: {geometry_info.get('span_mm', 0):.0f} mm, "
        f"Bay: {geometry_info.get('bay_width_mm', 0):.0f} mm | "
        f"Required Z: {Z_req_cm3:.1f} cm³</sub>"
    )
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center'
        }
        xaxis_title="Section Depth (mm)",
        yaxis_title="Section Modulus (cm³)",
        xaxis=dict(range=[x_min, x_max]),
        yaxis=dict(range=[0, y_max]),
        height=650,
        hovermode='closest',
        plot_bgcolor='white'
    )
    
    return fig


def generate_sls_plot(
    df: pd.DataFrame,
    I_req_cm4: float,
    defl_limit_mm: float,
    material: str,
    sls_case_name: str,
    geometry_info: Dict
) -> go.Figure:
    """
    Generate SLS plot showing moment of inertia vs depth.
    
    Parameters
    ----------
    df : pd.DataFrame
        Filtered section database
    I_req_cm4 : float
        Required moment of inertia (cm⁴)
    defl_limit_mm : float
        Deflection limit (mm)
    material : str
        Material type
    sls_case_name : str
        Name of governing SLS case
    geometry_info : Dict
        Dictionary with geometry parameters for title
        
    Returns
    -------
    go.Figure
        Plotly figure
    """
    depths = df['D'].values
    I_available = df['I'].values  # Already in cm⁴
    reinf = df['REINF'].values
    profiles = df['NAME'].values
    suppliers = df['SUPPLIER'].values
    
    # Determine pass/fail
    sls_passed = I_available >= I_req_cm4
    
    # Colors and symbols
    sls_colors = ['seagreen' if p else 'darkred' for p in sls_passed]
    sls_symbols = ['square' if r else 'circle' for r in reinf]
    
    # Hover text
    sls_hover = [
        f"{profiles[i]}<br>Supplier: {suppliers[i]}<br>"
        f"Depth: {depths[i]:.0f} mm<br>"
        f"I: {I_available[i]:.2f} cm⁴<br>"
        f"SLS: {'Pass' if sls_passed[i] else 'Fail'}"
        for i in range(len(depths))
    ]
    
    # Plot range
    x_min = np.min(depths) * 0.95 if len(depths) > 0 else 0
    x_max = np.max(depths) * 1.05 if len(depths) > 0 else 100
    y_max = 4 * I_req_cm4
    
    # Create figure
    fig = go.Figure()
    
    # Pass region (below requirement - inverted for deflection/inertia)
    fig.add_shape(
        type="rect",
        x0=x_min, x1=x_max,
        y0=I_req_cm4, y1=y_max,
        fillcolor=TT_LightBlue,
        opacity=0.2,
        line_width=0,
        layer='below'
    )
    
    # Fail region (above requirement - inverted for deflection/inertia)
    fig.add_shape(
        type="rect",
        x0=x_min, x1=x_max,
        y0=0, y1=I_req_cm4,
        fillcolor=TT_MidBlue,
        opacity=0.2,
        line_width=0,
        layer='below'
    )
    
    # Scatter plot
    fig.add_trace(go.Scatter(
        x=depths,
        y=I_available,
        mode='markers',
        marker=dict(
            color=sls_colors,
            symbol=sls_symbols,
            size=15,
            line=dict(color='black', width=1)
        ),
        text=sls_hover,
        hoverinfo='text',
        showlegend=False
    ))
    
    # Layout
    title_text = (
        f"{material} SLS Design ({sls_case_name})<br>"
        f"<sub>Span: {geometry_info.get('span_mm', 0):.0f} mm, "
        f"Bay: {geometry_info.get('bay_width_mm', 0):.0f} mm | "
        f"Deflection Limit: {defl_limit_mm:.1f} mm, Required I: {I_req_cm4:.1f} cm⁴</sub>"
    )
    
    fig.update_layout(
        title={
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="Section Depth (mm)",
        yaxis_title="Moment of Inertia I (cm⁴)",
        xaxis=dict(range=[x_min, x_max]),
        yaxis=dict(range=[0, y_max]),
        height=650,
        hovermode='closest',
        plot_bgcolor='white'
    )
    
    return fig


def generate_utilisation_plot(
    df: pd.DataFrame,
    Z_req_cm3: float,
    I_req_cm4: float,
    view_option: str = "Isometric: Overview"
) -> Tuple[go.Figure, Optional[str]]:
    """
    Generate 3D utilisation plot showing ULS vs SLS vs Depth.
    
    Parameters
    ----------
    df : pd.DataFrame
        Filtered section database
    Z_req_cm3 : float
        Required section modulus (cm³)
    I_req_cm4 : float
        Required moment of inertia (cm⁴)
    view_option : str
        Camera view option
        
    Returns
    -------
    Tuple[go.Figure, Optional[str]]
        Plotly figure and recommended profile text
    """
    depths = df['D'].values
    Z_available = df['Z'].values
    I_available = df['I'].values
    profiles = df['NAME'].values
    suppliers = df['SUPPLIER'].values
    
    # Calculate utilisations
    uls_util = []
    sls_util = []
    depths_safe = []
    profiles_safe = []
    suppliers_safe = []
    
    for i in range(len(depths)):
        if Z_available[i] == 0 or I_available[i] == 0:
            continue
        
        uls_ratio = Z_req_cm3 / Z_available[i]
        sls_ratio = I_req_cm4 / I_available[i]
        
        # Only include sections that pass both checks
        if uls_ratio <= 1.0 and sls_ratio <= 1.0:
            uls_util.append(uls_ratio)
            sls_util.append(sls_ratio)
            depths_safe.append(depths[i])
            profiles_safe.append(profiles[i])
            suppliers_safe.append(suppliers[i])
    
    # Determine recommended profile (shallowest with highest utilisation)
    recommended_text = None
    if len(depths_safe) > 0:
        min_depth = min(depths_safe)
        indices = [i for i, d in enumerate(depths_safe) if d == min_depth]
        
        if indices:
            # Calculate distance from origin for tie-breaking
            distances = [np.sqrt(uls_util[i]**2 + sls_util[i]**2) for i in indices]
            rec_idx = indices[np.argmax(distances)]
            recommended_text = f"Recommended: {suppliers_safe[rec_idx]}: {profiles_safe[rec_idx]}"
    else:
        recommended_text = "No suitable sections found - adjust parameters or use custom section"
    
    # Calculate marker sizes based on distance from origin
    if len(uls_util) > 0:
        distances = np.sqrt(np.array(uls_util)**2 + np.array(sls_util)**2)
        sizes = 10 + (distances / np.sqrt(2)) * 20
    else:
        sizes = 15
    
    # Create figure
    fig = go.Figure(data=[go.Scatter3d(
        x=uls_util,
        y=sls_util,
        z=depths_safe,
        mode='markers',
        marker=dict(
            size=sizes,
            color=depths_safe,
            colorscale='Viridis',
            colorbar=dict(title="Depth (mm)"),
            line=dict(color='black', width=0.5)
        ),
        text=[
            f"{suppliers_safe[i]}: {profiles_safe[i]}<br>"
            f"Depth: {depths_safe[i]:.0f} mm<br>"
            f"ULS Util: {uls_util[i]:.2%}<br>"
            f"SLS Util: {sls_util[i]:.2%}"
            for i in range(len(depths_safe))
        ],
        hoverinfo='text',
        showlegend=False
    )])
    
    # Set camera view
    if view_option == "Isometric: Overview":
        camera = dict(eye=dict(x=1.25, y=1.25, z=1.25))
    elif view_option == "XY Plane: Utilisation":
        camera = dict(eye=dict(x=0, y=0, z=2.5), projection=dict(type='orthographic'))
    elif view_option == "XZ Plane: Section Depth":
        camera = dict(eye=dict(x=0, y=2.5, z=0), projection=dict(type='orthographic'))
    else:
        camera = dict(eye=dict(x=1.25, y=1.25, z=1.25))
    
    # Layout
    max_depth = max(depths_safe) if len(depths_safe) > 0 else 100
    
    fig.update_layout(
        height=650,
        title=f"3D Utilisation Plot<br><sub>{recommended_text}</sub>",
        scene=dict(
            xaxis=dict(range=[0.0, 1.0], title="ULS Utilisation"),
            yaxis=dict(range=[0.0, 1.0], title="SLS Utilisation"),
            zaxis=dict(range=[50, 1.05 * max_depth], title="Section Depth (mm)"),
            camera=camera
        ),
        plot_bgcolor='white'
    )
    
    return fig, recommended_text


def generate_section_table(
    df: pd.DataFrame,
    Z_req_cm3: float,
    I_req_cm4: float
) -> Tuple[pd.DataFrame, any]:
    """
    Generate styled section table with utilisation calculations.
    
    Parameters
    ----------
    df : pd.DataFrame
        Filtered section database
    Z_req_cm3 : float
        Required section modulus (cm³)
    I_req_cm4 : float
        Required moment of inertia (cm⁴)
        
    Returns
    -------
    Tuple[pd.DataFrame, styled DataFrame]
        Plain and styled dataframes
    """
    df_table = df.copy()
    
    # Calculate utilisations
    df_table['ULS Utilisation'] = Z_req_cm3 / df_table['Z']
    df_table['SLS Utilisation'] = I_req_cm4 / df_table['I']
    df_table['Max Utilisation'] = df_table[['ULS Utilisation', 'SLS Utilisation']].max(axis=1)
    
    # Separate passing and failing
    df_pass = df_table[df_table['Max Utilisation'] <= 1.0].copy()
    df_fail = df_table[df_table['Max Utilisation'] > 1.0].copy()
    
    # Sort passing by SLS utilisation (descending - most efficient first)
    df_pass = df_pass.sort_values(by='SLS Utilisation', ascending=False)
    
    # Sort failing by max utilisation (ascending - closest to passing first)
    df_fail = df_fail.sort_values(by='Max Utilisation', ascending=True)
    
    # Combine
    df_sorted = pd.concat([df_pass, df_fail], ignore_index=True)
    
    # Create display dataframe - using original column names
    df_display = df_sorted[['SUPPLIER', 'NAME', 'D', 'Z', 'I', 
                             'ULS Utilisation', 'SLS Utilisation']].copy()
    
    df_display.columns = ['Supplier', 'Profile Name', 'Depth (mm)', 'Z (cm³)', 
                          'I (cm⁴)', 'ULS Util.', 'SLS Util.']
    
    # Format columns
    df_display['Depth (mm)'] = df_display['Depth (mm)'].round(0).astype(int)
    df_display['Z (cm³)'] = df_display['Z (cm³)'].round(2)
    df_display['I (cm⁴)'] = df_display['I (cm⁴)'].round(2)
    df_display['ULS Util.'] = (df_display['ULS Util.'] * 100).round(1).astype(str) + '%'
    df_display['SLS Util.'] = (df_display['SLS Util.'] * 100).round(1).astype(str) + '%'
    
    # Create styled dataframe
    def highlight_rows(row):
        uls_val = float(row['ULS Util.'].strip('%')) / 100
        sls_val = float(row['SLS Util.'].strip('%')) / 100
        max_util = max(uls_val, sls_val)
        
        if max_util <= 1.0:
            # Passing - green gradient
            intensity = max_util
            return [f'background-color: rgba(0, 128, 0, {0.1 + intensity * 0.3})'] * len(row)
        else:
            # Failing - red gradient
            intensity = min((max_util - 1.0) * 2, 1.0)
            return [f'background-color: rgba(255, 0, 0, {0.1 + intensity * 0.3})'] * len(row)
    
    try:
        styled_df = df_display.style.apply(highlight_rows, axis=1)
    except:
        styled_df = df_display
    
    return df_display, styled_df


def section_selection_ui(
    container=None,
    geometry_info: Dict = None,
    material: str = "Aluminium",
    Z_req_cm3: float = 0.0,
    I_req_cm4: float = 0.0,
    defl_limit_mm: float = 0.0,
    uls_case_name: str = "ULS",
    sls_case_name: str = "SLS",
    excel_path: str = "data/mullion_profile_db.xlsx"
):
    """
    Render section selection UI with plots and tables.
    
    Parameters
    ----------
    container : streamlit container, optional
        Container to render UI in
    geometry_info : Dict
        Dictionary with span_mm and bay_width_mm
    material : str
        Material type
    Z_req_cm3 : float
        Required section modulus (cm³)
    I_req_cm4 : float
        Required moment of inertia (cm⁴)
    defl_limit_mm : float
        Deflection limit (mm)
    uls_case_name : str
        Name of governing ULS case
    sls_case_name : str
        Name of governing SLS case
    excel_path : str
        Path to Excel database
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("section_selection_ui requires streamlit") from e
    
    parent = container if container is not None else st
    
    if geometry_info is None:
        geometry_info = {'span_mm': 0, 'bay_width_mm': 0}
    
    # Section header
    parent.markdown("### Section Selection")
    parent.markdown("---")
    
    # CACHED DATABASE LOADING - Only reads once per material+path combination
    @st.cache_data(show_spinner="Loading section database...")
    def cached_load_database(material: str, excel_path: str) -> pd.DataFrame:
        """Cached version of load_section_database"""
        return load_section_database(material, excel_path)
    
    # Load section database (cached!)
    try:
        df_all = cached_load_database(material, excel_path)
    except Exception as e:
        parent.error(f"Failed to load section database: {e}")
        return
    
    # Get unique suppliers
    all_suppliers = sorted(df_all['SUPPLIER'].unique())
    
    # Filters in sidebar or expander
    parent.markdown("#### Filters")
    
    filter_col1, filter_col2 = parent.columns(2)
    
    with filter_col1:
        selected_suppliers = parent.multiselect(
            "Select Suppliers",
            options=all_suppliers,
            default=all_suppliers,
            help="Filter sections by supplier"
        )
    
    with filter_col2:
        col_a, col_b = parent.columns(2)
        with col_a:
            include_reinf = parent.checkbox(
                "Include Reinforced",
                value=True,
                help="Include sections with reinforcement"
            )
        with col_b:
            include_unreinf = parent.checkbox(
                "Include Unreinforced",
                value=True,
                help="Include sections without reinforcement"
            )
    
    # Filter database
    df_filtered = filter_section_database(
        df_all,
        selected_suppliers,
        include_reinf,
        include_unreinf
    )
    
    if df_filtered.empty:
        parent.warning("No sections match the selected filters.")
        return
    
    parent.info(f"**{len(df_filtered)}** sections selected from database")
    
    parent.markdown("---")
    
    # Generate plots
    parent.markdown("#### Design Plots")
    
    parent.markdown("##### ULS: Section Modulus")
    uls_fig = generate_uls_plot(
        df_filtered,
        Z_req_cm3,
        material,
        uls_case_name,
        geometry_info
    )
    parent.plotly_chart(uls_fig, width='stretch')

    parent.markdown("##### SLS: Moment of Inertia")
    sls_fig = generate_sls_plot(
        df_filtered,
        I_req_cm4,
        defl_limit_mm,
        material,
        sls_case_name,
        geometry_info
    )
    parent.plotly_chart(sls_fig, width='stretch')

    # parent.markdown("##### 3D Utilisation")
    
    view_option = options=["Isometric: Overview","XY Plane: Utilisation","XZ Plane: Section Depth"]
    
    util_fig, recommended = generate_utilisation_plot(
        df_filtered,
        Z_req_cm3,
        I_req_cm4,
        view_option
    )
    # parent.plotly_chart(util_fig, width='stretch')
  
    parent.markdown("---")
    
    # Section table
    parent.markdown("#### Section Database")
    
    df_display, styled_df = generate_section_table(
        df_filtered,
        Z_req_cm3,
        I_req_cm4
    )
    
    # Display styled dataframe
    parent.dataframe(
        styled_df,
        width='stretch',
        hide_index=True
    )
    
    # Summary statistics
    parent.markdown("---")
    parent.markdown("#### Summary")
    
    n_pass = len(df_display[df_display['ULS Util.'].str.rstrip('%').astype(float) <= 100])
    n_fail = len(df_display) - n_pass
    
    sum_col1, sum_col2, sum_col3 = parent.columns(3)
    
    with sum_col1:
        parent.metric("Sections Passing", f"{n_pass}", 
                     delta=f"{n_pass/len(df_display)*100:.1f}%" if len(df_display) > 0 else "0%")
    
    with sum_col2:
        parent.metric("Sections Failing", f"{n_fail}",
                     delta=f"-{n_fail/len(df_display)*100:.1f}%" if len(df_display) > 0 else "0%",
                     delta_color="inverse")
    
    with sum_col3:
        if recommended:
            parent.success(f"✅ {recommended}")
        else:
            parent.warning("⚠️ No suitable sections")
    
    # Legend
    parent.caption("""
    **Legend:**
    - 🟢 Green background = Section passes both ULS and SLS
    - 🔴 Red background = Section fails ULS or SLS
    - ⬜ Square markers = Reinforced sections
    - ⚫ Circle markers = Unreinforced sections
    """)
