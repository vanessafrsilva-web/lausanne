import streamlit as st


def appliquer_styles():
    st.markdown("""
    <style>

    /* ===============================
       SIDEBAR
    =============================== */

    section[data-testid="stSidebar"] {
        background-color: #073763;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    /* boutons sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #1f4e79;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 6px 14px;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #2e6aa6;
    }

    /* ===============================
       FILE UPLOADER
    =============================== */

    [data-testid="stFileUploader"] {
        background-color: #1f4e79;
        padding: 10px;
        border-radius: 10px;
        border: none;
    }

    [data-testid="stFileUploader"] button {
        background-color: white !important;
        color: #073763 !important;
        border-radius: 6px;
        border: none;
    }

    /* ===============================
       FOND PRINCIPAL
    =============================== */

    [data-testid="stAppViewContainer"] {
        background-color: #f5f7fb;
    }

    .main {
        background-color: #f5f7fb;
    }

    /* ===============================
       TITRES
    =============================== */

    h1 {
        color: #073763;
        font-weight: 700;
    }

    h2, h3, h4 {
        color: #1f2c3d;
    }

    /* ===============================
       INPUTS
    =============================== */

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #dbe3f1;
        padding: 6px;
    }

    /* ===============================
       SELECTBOX
    =============================== */

    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 8px;
        border: 1px solid #dbe3f1;
    }

    /* ===============================
       METRICS
    =============================== */

    [data-testid="metric-container"] {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #e4e8ef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* ===============================
       TABLEAUX
    =============================== */

    [data-testid="stDataFrame"] {
        background-color: white !important;
        border-radius: 12px;
        border: 1px solid #dbe3f1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        overflow: hidden;
    }

    /* texte cellules */
    [data-testid="stDataFrame"] span {
        color: #1f2c3d !important;
    }

    /* ===============================
       TABS
    =============================== */

    button[data-baseweb="tab"] {
        font-size: 15px;
        color: #1f2c3d;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 3px solid #073763 !important;
        color: #073763;
        font-weight: 600;
    }

    </style>
    """, unsafe_allow_html=True)
