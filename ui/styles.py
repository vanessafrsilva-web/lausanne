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
        color: white !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background-color: #1f4e79;
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 6px 14px;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #2e6aa6;
        color: white !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #2a5d91;
        padding: 10px;
        border-radius: 12px;
        border: none;
    }

    [data-testid="stFileUploader"] button {
        background-color: white !important;
        color: #073763 !important;
        border-radius: 8px;
        border: none;
    }

    [data-testid="stFileUploader"] button:hover {
        background-color: #eaf2fb !important;
        color: #073763 !important;
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
       TEXTE PRINCIPAL
    =============================== */
    .block-container,
    .block-container p,
    .block-container label,
    .block-container div,
    .block-container span {
        color: #1f2c3d;
    }

    h1, h2, h3, h4 {
        color: #073763 !important;
    }

    /* Caption / petit texte */
    [data-testid="stCaptionContainer"] {
        color: #5b6575 !important;
    }

    /* Alertes info/success/warning */
    [data-testid="stAlertContainer"] * {
        color: #1f2c3d !important;
    }

    /* ===============================
       TABS
    =============================== */
    button[data-baseweb="tab"] {
        color: #1f2c3d !important;
        font-size: 15px;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #073763 !important;
        border-bottom: 3px solid #073763 !important;
        font-weight: 600;
    }

    /* ===============================
       INPUTS
    =============================== */
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background-color: white !important;
        color: #1f2c3d !important;
        border-radius: 8px;
        border: 1px solid #dbe3f1;
        padding: 6px;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #7a8699 !important;
    }

    /* ===============================
       SELECTBOX
    =============================== */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: white !important;
        color: #1f2c3d !important;
        border-radius: 8px;
        border: 1px solid #dbe3f1;
    }

    div[role="listbox"] {
        background-color: white !important;
        color: #1f2c3d !important;
    }
    /* HEADER TABLEAU */
[data-testid="stDataFrame"] .gdg-header {
    background-color: #ffffff !important;
    color: #000000 !important;
    font-weight: 600;
}

/* TEXTE HEADER */
[data-testid="stDataFrame"] .gdg-header span {
    color: #000000 !important;
}

/* LIGNE HEADER */
[data-testid="stDataFrame"] .gdg-header-row {
    background-color: #ffffff !important;
}

    /* ===============================
       RADIO / CHECKBOX
    =============================== */
    .stRadio label,
    .stCheckbox label {
        color: #1f2c3d !important;
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

    [data-testid="metric-container"] * {
        color: #073763 !important;
    }

    /* ===============================
       DATAFRAME / TABLE
    =============================== */
    [data-testid="stDataFrame"] {
        background-color: white !important;
        border-radius: 12px;
        border: 1px solid #dbe3f1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        overflow: hidden;
    }

    [data-testid="stDataFrame"] * {
        color: #1f2c3d !important;
    }

    /* ===============================
       DATA EDITOR
    =============================== */
    [data-testid="stDataEditor"] {
        background-color: white !important;
        border-radius: 12px;
        border: 1px solid #dbe3f1;
    }

    [data-testid="stDataEditor"] * {
        color: #1f2c3d !important;
    }

    </style>
    """, unsafe_allow_html=True)
