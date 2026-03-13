
import streamlit as st

def appliquer_styles():
    st.markdown("""
    <style>

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #f7f9fc;
    }

    /* Boutons sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #073763;
        color: white;
        border-radius: 8px;
        border: none;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1f4e79;
    }

    /* Fond principal */
    [data-testid="stAppViewContainer"] {
        background-color: #073763;
    }

    /* Table */
    [data-testid="stDataFrame"] {
        background-color: white !important;
        border-radius: 10px;
        border: 1px solid #dbe3f1;
    }

    [data-testid="stDataFrame"] span {
        color: #073763 !important;
    }

    </style>
    """, unsafe_allow_html=True)
