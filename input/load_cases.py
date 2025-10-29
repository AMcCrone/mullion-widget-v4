# input/load_cases.py
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import pandas as pd


@dataclass
class LoadCombination:
    """
    Represents a single load combination with partial factors.
    
    Attributes
    ----------
    name : str
        Description of the load case (e.g., "ULS 1: 1.5W + 0.75L")
    wind_factor : float
        Partial factor applied to wind load (γW)
    barrier_factor : float
        Partial factor applied to barrier load (γB)
    case_type : str
        Either "ULS" or "SLS"
    """
    name: str
    wind_factor: float
    barrier_factor: float
    case_type: str = "ULS"
    
    def __post_init__(self):
        if self.wind_factor < 0:
            raise ValueError("wind_factor must be non-negative")
        if self.barrier_factor < 0:
            raise ValueError("barrier_factor must be non-negative")
        if self.case_type not in ("ULS", "SLS"):
            raise ValueError("case_type must be 'ULS' or 'SLS'")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame"""
        return {
            "Load Case": self.name,
            "Wind Factor": self.wind_factor,
            "Barrier Factor": self.barrier_factor
        }
    
    @classmethod
    def from_dict(cls, data: Dict, case_type: str = "ULS") -> "LoadCombination":
        """Create from dictionary (e.g., from DataFrame row)"""
        return cls(
            name=data["Load Case"],
            wind_factor=data["Wind Factor"],
            barrier_factor=data["Barrier Factor"],
            case_type=case_type
        )


@dataclass
class LoadCaseSet:
    """
    Container for ULS and SLS load cases.
    
    Attributes
    ----------
    uls_cases : List[LoadCombination]
        List of ULS load combinations
    sls_cases : List[LoadCombination]
        List of SLS load combinations
    """
    uls_cases: List[LoadCombination] = field(default_factory=list)
    sls_cases: List[LoadCombination] = field(default_factory=list)
    
    def get_uls_dataframe(self) -> pd.DataFrame:
        """Convert ULS cases to DataFrame for UI display"""
        if not self.uls_cases:
            return self._default_uls_dataframe()
        return pd.DataFrame([case.to_dict() for case in self.uls_cases])
    
    def get_sls_dataframe(self) -> pd.DataFrame:
        """Convert SLS cases to DataFrame for UI display"""
        if not self.sls_cases:
            return self._default_sls_dataframe()
        return pd.DataFrame([case.to_dict() for case in self.sls_cases])
    
    def update_from_dataframes(self, uls_df: pd.DataFrame, sls_df: pd.DataFrame):
        """Update load cases from edited DataFrames"""
        self.uls_cases = [
            LoadCombination.from_dict(row.to_dict(), case_type="ULS")
            for _, row in uls_df.iterrows()
        ]
        self.sls_cases = [
            LoadCombination.from_dict(row.to_dict(), case_type="SLS")
            for _, row in sls_df.iterrows()
        ]
    
    def get_uls_dict(self) -> Dict[str, Tuple[float, float]]:
        """
        Convert ULS cases to dictionary format for calculations.
        
        Returns
        -------
        Dict[str, Tuple[float, float]]
            Dictionary with case names as keys and (wind_factor, barrier_factor) tuples
        """
        return {case.name: (case.wind_factor, case.barrier_factor) for case in self.uls_cases}
    
    def get_sls_dict(self) -> Dict[str, Tuple[float, float]]:
        """
        Convert SLS cases to dictionary format for calculations.
        
        Returns
        -------
        Dict[str, Tuple[float, float]]
            Dictionary with case names as keys and (wind_factor, barrier_factor) tuples
        """
        return {case.name: (case.wind_factor, case.barrier_factor) for case in self.sls_cases}
    
    @staticmethod
    def _default_uls_dataframe() -> pd.DataFrame:
        """Return default EN 1990 ULS load cases"""
        return pd.DataFrame({
            'Load Case': [
                'ULS 1: 1.5W + 0.75L',
                'ULS 2: 0.75W + 1.5L',
                'ULS 3: 1.5W',
                'ULS 4: 1.5L'
            ],
            'Wind Factor': [1.5, 0.75, 1.5, 0.0],
            'Barrier Factor': [0.75, 1.5, 0.0, 1.5]
        })
    
    @staticmethod
    def _default_sls_dataframe() -> pd.DataFrame:
        """Return default EN 1990 SLS load cases"""
        return pd.DataFrame({
            'Load Case': ['SLS 1: W', 'SLS 2: L'],
            'Wind Factor': [1.0, 0.0],
            'Barrier Factor': [0.0, 1.0]
        })
    
    @classmethod
    def create_en1990_defaults(cls) -> "LoadCaseSet":
        """Create LoadCaseSet with EN 1990 default cases"""
        uls_cases = [
            LoadCombination("ULS 1: 1.5W + 0.75L", 1.5, 0.75, "ULS"),
            LoadCombination("ULS 2: 0.75W + 1.5L", 0.75, 1.5, "ULS"),
            LoadCombination("ULS 3: 1.5W", 1.5, 0.0, "ULS"),
            LoadCombination("ULS 4: 1.5L", 0.0, 1.5, "ULS")
        ]
        sls_cases = [
            LoadCombination("SLS 1: W", 1.0, 0.0, "SLS"),
            LoadCombination("SLS 2: L", 0.0, 1.0, "SLS")
        ]
        return cls(uls_cases=uls_cases, sls_cases=sls_cases)
    
    @classmethod
    def create_custom_defaults(cls) -> "LoadCaseSet":
        """Create LoadCaseSet with custom load cases"""
        uls_cases = [
            LoadCombination("ULS 1: W + L", 1.0, 1.0, "ULS"),
            LoadCombination("ULS 2: 0.5W + 1.6L", 0.5, 1.6, "ULS"),
            LoadCombination("ULS 3: W + 0.5L", 1.0, 0.5, "ULS"),
            LoadCombination("ULS 4: W", 1.0, 0.0, "ULS")
        ]
        sls_cases = [
            LoadCombination("SLS 1: W + L", 1.0, 1.0, "SLS"),
            LoadCombination("SLS 2: 0.75L", 0.0, 0.75, "SLS"),
            LoadCombination("SLS 3: 0.6W", 0.6, 0.0, "SLS"),
            LoadCombination("SLS 4: 0.45W + 0.75L", 0.45, 0.75, "SLS")
        ]
        return cls(uls_cases=uls_cases, sls_cases=sls_cases)


def load_cases_ui(container=None, key_prefix: str = "loadcase") -> LoadCaseSet:
    """
    Render load case definition UI with editable dataframes.
    
    Parameters
    ----------
    container : streamlit container, optional
        Container to render UI in (if None, uses st directly)
    key_prefix : str
        Prefix for session state keys
        
    Returns
    -------
    LoadCaseSet
        Container with all ULS and SLS load combinations
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("load_cases_ui requires streamlit but it isn't available.") from e

    parent = container if container is not None else st

    # Initialize session state for load cases if not present
    if "load_case_set" not in st.session_state:
        st.session_state.load_case_set = LoadCaseSet.create_en1990_defaults()
    
    if "uls_cases_df" not in st.session_state:
        st.session_state.uls_cases_df = st.session_state.load_case_set.get_uls_dataframe()
    
    if "sls_cases_df" not in st.session_state:
        st.session_state.sls_cases_df = st.session_state.load_case_set.get_sls_dataframe()

    # Section header
    parent.markdown("### 📊 Load Case Definition")
    parent.markdown("---")
    
    parent.markdown("""
    Define the load combinations for Ultimate Limit State (ULS) and Serviceability Limit State (SLS) analyses.
    Load factors (partial factors) are applied to wind and barrier loads according to design codes.
    
    **Note:** You can add, remove, or modify rows in the tables below.
    """)
    
    # ========== ULS LOAD CASES ==========
    parent.markdown("#### Ultimate Limit State (ULS) Load Cases")
    parent.markdown("*ULS checks ensure the structure has adequate strength*")
    
    edited_uls = parent.data_editor(
        st.session_state.uls_cases_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{key_prefix}_uls_editor",
        column_config={
            "Load Case": st.column_config.TextColumn(
                "Load Case",
                help="Description of load case (e.g., '1.5W + 0.75L')",
                width="medium"
            ),
            "Wind Factor": st.column_config.NumberColumn(
                "Wind Factor (γW)",
                help="Partial factor applied to wind load",
                min_value=0.0,
                max_value=2.0,
                step=0.05,
                format="%.2f",
                width="small"
            ),
            "Barrier Factor": st.column_config.NumberColumn(
                "Barrier Factor (γL)",
                help="Partial factor applied to barrier load",
                min_value=0.0,
                max_value=2.0,
                step=0.05,
                format="%.2f",
                width="small"
            )
        },
        hide_index=True
    )
    
    st.session_state.uls_cases_df = edited_uls
    
    # Display number of ULS cases
    parent.caption(f"📋 {len(edited_uls)} ULS load case(s) defined")
    
    parent.markdown("---")
    
    # ========== SLS LOAD CASES ==========
    parent.markdown("#### Serviceability Limit State (SLS) Load Cases")
    parent.markdown("*SLS checks ensure the structure has acceptable deflections*")
    
    edited_sls = parent.data_editor(
        st.session_state.sls_cases_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{key_prefix}_sls_editor",
        column_config={
            "Load Case": st.column_config.TextColumn(
                "Load Case",
                help="Description of load case (e.g., 'W' or 'L')",
                width="medium"
            ),
            "Wind Factor": st.column_config.NumberColumn(
                "Wind Factor (γW)",
                help="Partial factor applied to wind load",
                min_value=0.0,
                max_value=1.5,
                step=0.05,
                format="%.2f",
                width="small"
            ),
            "Barrier Factor": st.column_config.NumberColumn(
                "Barrier Factor (γL)",
                help="Partial factor applied to barrier load",
                min_value=0.0,
                max_value=1.5,
                step=0.05,
                format="%.2f",
                width="small"
            )
        },
        hide_index=True
    )
    
    st.session_state.sls_cases_df = edited_sls
    
    # Display number of SLS cases
    parent.caption(f"📋 {len(edited_sls)} SLS load case(s) defined")
    
    parent.markdown("---")
    
    # ========== LOAD CASE SUMMARY ==========
    parent.markdown("---")
    parent.markdown("#### 📈 Load Case Summary")
    
    sum_col1, sum_col2 = parent.columns(2)
    
    with sum_col1:
        parent.info(f"""
        **ULS Load Cases:** {len(edited_uls)}
        
        Maximum factors:
        - Wind: {edited_uls['Wind Factor'].max():.2f} (γW,max)
        - Barrier: {edited_uls['Barrier Factor'].max():.2f} (γL,max)
        """)
    
    with sum_col2:
        parent.info(f"""
        **SLS Load Cases:** {len(edited_sls)}
        
        Maximum factors:
        - Wind: {edited_sls['Wind Factor'].max():.2f} (γW,max)
        - Barrier: {edited_sls['Barrier Factor'].max():.2f} (γL,max)
        """)
    
    # Update LoadCaseSet from edited dataframes
    load_case_set = LoadCaseSet()
    load_case_set.update_from_dataframes(edited_uls, edited_sls)
    st.session_state.load_case_set = load_case_set
    
    return load_case_set


def get_load_case_description() -> str:
    """
    Return a description of common load case standards for reference.
    
    Returns
    -------
    str
        Markdown-formatted description
    """
    return """
    ### Common Load Case Standards
    
    #### EN 1990 (Eurocode 0) - Typical Combinations
    
    **ULS (Ultimate Limit State):**
    - Combination 1: 1.5W + 0.75L (Wind dominant)
    - Combination 2: 0.75W + 1.5L (Barrier dominant)
    - Combination 3: 1.5W (Wind only)
    - Combination 4: 1.5L (Barrier only)
    
    **SLS (Serviceability Limit State):**
    - Combination 1: 1.0W (Characteristic wind)
    - Combination 2: 1.0L (Characteristic barrier)
    
    #### ASCE 7 - US Building Code
    - Different factor combinations may apply
    - Consult local jurisdiction for specific requirements
    
    #### Custom Combinations
    - Can be defined based on project-specific requirements
    - Always verify with local building codes
    """
