# utils/styles.py
"""Styles CSS + helpers UI — SRM Souss-Massa."""

import base64
from pathlib import Path


def get_logo_base64() -> str:
    logo_path = Path(__file__).parent.parent / "assets" / "logo_srm.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


class Icon:
    @staticmethod
    def _base(path, size=16, stroke="currentColor", sw=2):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
        )

    DASHBOARD = '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>'
    CHART_BAR = '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>'
    CLIPBOARD = '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>'
    CHECK_CIRCLE = '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
    SHIELD = '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
    USER = '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'
    USERS = '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    CLOCK = '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
    CALENDAR = '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>'
    MAP_PIN = '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'
    DATABASE = '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
    ARCHIVE = '<polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/>'
    FILE_TEXT = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'
    DROPLET = '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>'
    INBOX = '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
    FOLDER = '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
    ACTIVITY = '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
    LOCK = '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
    EDIT = '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>'
    PLUS = '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'
    INFO = '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
    ALERT = '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
    X = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
    TRENDING_UP = '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>'
    EYE = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'
    FILTER = '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>'
    LAYERS = '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'
    MESSAGE = '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'

    @classmethod
    def render(cls, name, size=16, color="currentColor", sw=2):
        p = getattr(cls, name.upper(), None)
        return cls._base(p, size, color, sw) if p else ""


def get_global_css(sidebar_open: bool = True) -> str:
    """Une seule balise <style>, concaténation simple (pas de f-string sur le CSS)."""

    if sidebar_open:
        sidebar_css = """
        section[data-testid="stSidebar"] {
            display: flex !important;
            flex-direction: column !important;
            visibility: visible !important;
            transform: none !important;
            position: relative !important;
            top: 0 !important;
            left: 0 !important;
            width: 260px !important;
            min-width: 260px !important;
            max-width: 260px !important;
            margin-left: 0 !important;
            background-color: #FFFFFF !important;
            border-right: 1px solid #E5E7EB !important;
            z-index: 100 !important;
        }
        section.main, [data-testid="stMain"] {
            flex: 1 !important;
            width: calc(100vw - 260px) !important;
            max-width: calc(100vw - 260px) !important;
        }
        """
    else:
        sidebar_css = """
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            overflow: hidden !important;
        }
        section.main, [data-testid="stMain"] {
            flex: 1 !important;
            width: 100vw !important;
            max-width: 100vw !important;
        }
        """

    # IMPORTANT : une seule balise <style> — concaténation, pas de f"{css}"
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { box-sizing: border-box !important; }
    html, body, .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #FFFFFF !important;
        color: #111827 !important;
        font-size: 13px !important;
    }

    [data-testid="stAppViewContainer"] {
        display: flex !important;
        flex-direction: row !important;
    }
    """ + sidebar_css + """

    section[data-testid="stSidebar"] > div { background-color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .block-container { padding: 1rem 0.75rem !important; }

    .block-container {
        padding: 1.5rem 2rem 3rem 2rem !important;
        max-width: 1400px !important;
        width: 100% !important;
    }

    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
    [data-testid="stExpandSidebarButton"], header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Boutons nav sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        color: #4B5563 !important;
        text-align: left !important;
        padding: 0.55rem 0.85rem !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #F3F4F6 !important;
        color: #111827 !important;
    }
    section[data-testid="stSidebar"] .nav-active .stButton > button {
        background: #F3F4F6 !important;
        color: #111827 !important;
        font-weight: 600 !important;
    }

    /* Branding sidebar */
    .sb-logo-wrap {
        text-align: center;
        padding: 0.25rem 0.5rem 1rem;
        border-bottom: 1px solid #F3F4F6;
        margin-bottom: 0.75rem;
    }
    .sb-logo-img {
        max-width: 100px !important;
        margin: 0 auto 0.5rem !important;
        display: block !important;
    }
    .sb-logo-title {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }
    .sb-logo-sub {
        font-size: 0.65rem !important;
        color: #9CA3AF !important;
        font-weight: 600;
        margin-top: 0.15rem;
        letter-spacing: 1px;
    }

    .sb-user {
        padding: 0.75rem !important;
        background: #F9FAFB !important;
        border-radius: 8px !important;
        margin-bottom: 0.5rem !important;
        border: 1px solid #F3F4F6;
    }
    .sb-user-avatar {
        width: 34px; height: 34px; border-radius: 50%;
        background: #111827; color: #FFF !important;
        display: flex; align-items: center; justify-content: center;
        font-weight: 600; font-size: 0.8rem; margin-bottom: 0.5rem;
    }
    .sb-user-name { font-size: 0.82rem !important; font-weight: 600 !important; color: #111827 !important; }
    .sb-user-role { font-size: 0.7rem !important; color: #6B7280 !important; margin-top: 0.15rem; }
    .sb-user-province {
        display: inline-flex; align-items: center; gap: 0.25rem;
        font-size: 0.68rem !important; color: #4B5563 !important;
        margin-top: 0.45rem; padding: 0.15rem 0.45rem;
        background: #FFF; border: 1px solid #E5E7EB; border-radius: 4px;
    }
    /* ══════════ SIDEBAR : Sections séparées et claires ══════════ */
    .nav-section {
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        color: #6B7280 !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        padding: 0.9rem 0.85rem 0.35rem !important;
        margin-top: 0.75rem;
        border-top: 1px solid #E5E7EB;
        position: relative;
    }

    /* Première section : pas de border-top */
    .nav-section.first-section {
        border-top: none !important;
        margin-top: 0.25rem !important;
        padding-top: 0.5rem !important;
    }

    /* Petite icône colorée à côté du titre de section */
    .nav-section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem 0.25rem !important;
    }

    .nav-section-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }

    .nav-section-label {
        font-size: 0.68rem;
        font-weight: 700;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }

    /* Container de chaque section pour un fond léger */
    .nav-section-wrapper {
        background: #FAFBFC;
        border: 1px solid #EEF0F2;
        border-radius: 8px;
        padding: 0.35rem 0.25rem;
        margin: 0.4rem 0 0.6rem 0;
    }

    /* Boutons dans un wrapper de section */
    .nav-section-wrapper .stButton > button {
        background: transparent !important;
        color: #4B5563 !important;
        text-align: left !important;
        padding: 0.5rem 0.8rem !important;
        border-radius: 5px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
        border: none !important;
    }
    .nav-section-wrapper .stButton > button:hover {
        background: #FFFFFF !important;
        color: #111827 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    .nav-section-wrapper .nav-active .stButton > button {
        background: #111827 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    .nav-section-wrapper .nav-active .stButton > button:hover {
        background: #1F2937 !important;
    }

    /* Bouton toggle compact « / » */
    .srm-toggle-open button,
    button[key="btn_sidebar_open"],
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        border-radius: 8px !important;
    }

    /* Page */
    .page-header { margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #E5E7EB; }
    .ph-title { font-size: 1.5rem !important; font-weight: 700 !important; color: #111827 !important; margin: 0; }
    .ph-sub { font-size: 0.875rem !important; color: #6B7280 !important; margin-top: 0.25rem; }

    .m-card { background: #FFF !important; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1.25rem; }
    .m-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; }
    .m-card-label { font-size: 0.72rem !important; font-weight: 600 !important; color: #6B7280 !important; text-transform: uppercase; letter-spacing: 0.3px; }
    .m-card-icon { color: #9CA3AF; display: flex; }
    .m-card-value { font-size: 1.75rem !important; font-weight: 700 !important; color: #111827 !important; line-height: 1.1; }
    .m-card-sub { font-size: 0.72rem !important; color: #9CA3AF !important; margin-top: 0.3rem; }

    .section { background: #FFF !important; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.25rem; }
    .section-title { display: flex; align-items: center; gap: 0.5rem; font-size: 0.95rem !important; font-weight: 600 !important; color: #111827 !important; margin-bottom: 0.25rem; }
    .section-sub { font-size: 0.8rem !important; color: #6B7280 !important; margin-bottom: 1rem; }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #FFF !important;
        color: #111827 !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #111827 !important;
        box-shadow: 0 0 0 3px rgba(17,24,39,0.08) !important;
    }
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] { display: none !important; }
    input[type="number"]::-webkit-inner-spin-button,
    input[type="number"]::-webkit-outer-spin-button { -webkit-appearance: none !important; }

    .stButton > button {
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.55rem 1rem !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="primary"] {
        background: #111827 !important;
        color: #FFF !important;
        border: 1px solid #111827 !important;
    }
    .stButton > button[kind="primary"]:hover { background: #1F2937 !important; }
    .btn-success .stButton > button { background: #059669 !important; color: #FFF !important; border-color: #059669 !important; }
    .btn-danger .stButton > button { background: #FFF !important; color: #DC2626 !important; border-color: #FCA5A5 !important; }
    .btn-danger .stButton > button:hover { background: #FEF2F2 !important; border-color: #DC2626 !important; }

    .badge {
        display: inline-flex; align-items: center; gap: 0.35rem;
        padding: 0.2rem 0.55rem; border-radius: 4px;
        font-size: 0.72rem; font-weight: 500; border: 1px solid transparent;
    }
    .badge-slate { background: #F1F5F9; color: #475569; border-color: #E2E8F0; }
    .badge-blue { background: #EFF6FF; color: #1D4ED8; border-color: #DBEAFE; }
    .badge-green { background: #F0FDF4; color: #15803D; border-color: #DCFCE7; }
    .badge-red { background: #FEF2F2; color: #B91C1C; border-color: #FEE2E2; }
    .badge-amber { background: #FFFBEB; color: #B45309; border-color: #FEF3C7; }
    .badge-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }

    .notice {
        display: flex; align-items: flex-start; gap: 0.6rem;
        padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.85rem;
        margin-bottom: 1rem; border: 1px solid; line-height: 1.5;
    }
    .notice-info { background: #F0F9FF; border-color: #E0F2FE; color: #075985; }
    .notice-success { background: #F0FDF4; border-color: #DCFCE7; color: #14532D; }
    .notice-warning { background: #FFFBEB; border-color: #FEF3C7; color: #78350F; }
    .notice-error { background: #FEF2F2; border-color: #FEE2E2; color: #7F1D1D; }

    .empty { text-align: center; padding: 2.5rem 1.5rem; color: #6B7280; }
    .empty-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 48px; height: 48px; border-radius: 50%;
        background: #F3F4F6; color: #9CA3AF; margin: 0 auto 0.85rem;
    }
    .empty-title { font-size: 0.9rem !important; font-weight: 600 !important; color: #374151 !important; }
    .empty-sub { font-size: 0.8rem !important; color: #9CA3AF !important; margin-top: 0.2rem; }

    .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #E5E7EB !important; gap: 0 !important; }
    .stTabs [data-baseweb="tab"] { font-weight: 500 !important; color: #6B7280 !important; }
    .stTabs [aria-selected="true"] { color: #111827 !important; font-weight: 600 !important; }

    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border: 1px solid #E5E7EB !important; border-radius: 6px !important;
    }
    [data-testid="stExpander"] { border: 1px solid #E5E7EB !important; border-radius: 6px !important; }

    .form-cat {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.6rem 0.9rem; background: #F9FAFB;
        border-left: 3px solid #111827; border-radius: 4px;
        margin: 1.25rem 0 0.75rem; font-weight: 600; font-size: 0.85rem; color: #111827 !important;
    }

    /* Bouton fermer sidebar : petit, sans casser la nav */
    section[data-testid="stSidebar"] .srm-close-row button {
        min-width: 2rem !important;
        width: 2rem !important;
        height: 2rem !important;
        padding: 0 !important;
        border-radius: 8px !important;
        border: 1px solid #E5E7EB !important;
        background: #FFFFFF !important;
        color: #4B5563 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .srm-close-row button:hover {
        background: #F3F4F6 !important;
        color: #111827 !important;
    }

    /* Bouton ouvrir » quand sidebar fermée */
    .srm-open-wrap button {
        min-width: 2rem !important;
        width: 2rem !important;
        height: 2rem !important;
        padding: 0 !important;
        border-radius: 8px !important;
        border: 1px solid #E5E7EB !important;
        background: #FFFFFF !important;
        color: #4B5563 !important;
    }

    </style>
    """
    return css



def get_login_css() -> str:
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {
        font-family: 'Inter', sans-serif !important;
        background: #F9FAFB !important;
        font-size: 14px !important;
    }

    #MainMenu, footer, [data-testid="stToolbar"],
    header[data-testid="stHeader"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    /* Centrage vertical de la page */
    .block-container {
        padding: 0 1rem !important;
        max-width: 100% !important;
        min-height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }

    /* Carte unique (formulaire) */
    [data-testid="stForm"] {
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 14px !important;
        padding: 2rem 2.25rem 1.75rem 2.25rem !important;
        box-shadow: 0 8px 24px rgba(17, 24, 39, 0.06) !important;
        max-width: 440px !important;
        margin: 0 auto !important;
    }

    /* En-tête logo + titre */
    .login-header {
        text-align: center;
        padding: 0.25rem 0 1.35rem 0;
        margin: 0 0 1.35rem 0;
        /* Ligne de séparation nette */
        border-bottom: 1px solid #E5E7EB;
    }

    .login-logo-img {
        max-width: 88px !important;
        margin: 0 auto 0.85rem auto !important;
        display: block !important;
        background: transparent !important;
    }

    .login-title {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
        margin: 0 !important;
        line-height: 1.3 !important;
    }

    .login-sub {
        font-size: 0.85rem !important;
        color: #6B7280 !important;
        margin-top: 0.35rem !important;
    }

    /* Champs */
    [data-testid="stForm"] .stTextInput > label {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: #374151 !important;
    }

    [data-testid="stForm"] .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 1px solid #D1D5DB !important;
        padding: 0.65rem 0.85rem !important;
    }

    [data-testid="stForm"] .stTextInput > div > div > input:focus {
        border-color: #111827 !important;
        box-shadow: 0 0 0 3px rgba(17,24,39,0.08) !important;
    }

    /* Bouton */
    button[data-testid="baseButton-primaryFormSubmit"],
    [data-testid="stForm"] button[kind="primaryFormSubmit"],
    [data-testid="stForm"] button[type="submit"] {
        background: #111827 !important;
        color: #FFF !important;
        border-radius: 8px !important;
        width: 100% !important;
        height: 2.6rem !important;
        font-weight: 600 !important;
        margin-top: 0.35rem !important;
        border: 1px solid #111827 !important;
    }

    button[data-testid="baseButton-primaryFormSubmit"]:hover,
    [data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
        background: #1F2937 !important;
    }

    .login-footer {
        text-align: center;
        font-size: 0.75rem;
        color: #9CA3AF;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        line-height: 1.5;
    }






    /* Style du bouton "Mot de passe oublié" ou "Retour" (qui sont hors du form) */
    div[data-testid="stMain"] button[kind="secondary"] {
        background: transparent !important;
        color: #4B5563 !important;
        border: none !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0 !important;
        margin-top: 0.5rem !important;
    }

    div[data-testid="stMain"] button[kind="secondary"]:hover {
        color: #111827 !important;
        background: transparent !important;
        text-decoration: underline !important;
    }
    </style>
    """


def render_page_header(title, subtitle=""):
    sub = f'<div class="ph-sub">{subtitle}</div>' if subtitle else ''
    return f'<div class="page-header"><div class="ph-title">{title}</div>{sub}</div>'


def render_metric(label, value, icon_name="", sub="", trend=None):
    icon_html = f'<span class="m-card-icon">{Icon.render(icon_name, size=18)}</span>' if icon_name else ''
    sub_html = f'<div class="m-card-sub">{sub}</div>' if sub else ''
    trend_html = ""
    if trend:
        val, direction = trend
        arrow = "▲" if direction == "up" else "▼" if direction == "down" else "●"
        color = "#059669" if direction == "up" else "#DC2626" if direction == "down" else "#6B7280"
        trend_html = f'<div style="color:{color};font-size:0.75rem;margin-top:0.3rem;font-weight:600;">{arrow} {val}</div>'
    return (
        f'<div class="m-card"><div class="m-card-header"><div class="m-card-label">{label}</div>'
        f'{icon_html}</div><div class="m-card-value">{value}</div>{sub_html}{trend_html}</div>'
    )


def render_section_open(title, icon_name="", subtitle=""):
    icon_html = Icon.render(icon_name, 16, "#6B7280") if icon_name else ''
    sub_html = f'<div class="section-sub">{subtitle}</div>' if subtitle else ''
    return f'<div class="section"><div class="section-title">{icon_html}<span>{title}</span></div>{sub_html}'


def render_section_close():
    return "</div>"


def render_notice(message, variant="info"):
    icons = {
        "info": Icon.render("INFO", 16),
        "success": Icon.render("CHECK_CIRCLE", 16),
        "warning": Icon.render("ALERT", 16),
        "error": Icon.render("X", 16),
    }
    return (
        f'<div class="notice notice-{variant}">'
        f'<span>{icons.get(variant, icons["info"])}</span><span>{message}</span></div>'
    )


def render_empty(icon_name, title, subtitle=""):
    sub = f'<div class="empty-sub">{subtitle}</div>' if subtitle else ''
    return (
        f'<div class="empty"><div class="empty-icon">{Icon.render(icon_name, 22)}</div>'
        f'<div class="empty-title">{title}</div>{sub}</div>'
    )


def render_form_category(icon_name, title):
    return (
        f'<div class="form-cat">{Icon.render(icon_name, 14, "#111827")}'
        f'<span>{title}</span></div>'
    )


def get_status_badge(status):
    config = {
        "brouillon": ("Brouillon", "slate"),
        "soumis": ("Soumis", "blue"),
        "valide_dp": ("Validé DP", "amber"),
        "rejete_dp": ("Rejeté DP", "red"),
        "valide_regional": ("Validé Régional", "green"),
        "rejete_regional": ("Rejeté Régional", "red"),
        "en_cours_validation_dp": ("En cours val. DP", "blue"),
        "en_cours_validation_regional": ("En cours val. Rég.", "amber"),
        "partiellement_rejete_dp": ("Partiel. rejeté DP", "red"),
        "partiellement_rejete_regional": ("Partiel. rejeté Rég.", "red"),
        "modif_admin_dp": ("En modif. Admin DP", "amber"),
        "modif_agent_dp": ("En modif. Agent", "amber"),
        "en_modification_admin_dp": ("En modif. Admin DP", "amber"),
        "en_modification_agent": ("En modif. Agent", "amber"),
    }
    label, color = config.get(status, (status, "slate"))
    dots = {"slate": "#64748B", "blue": "#2563EB", "green": "#16A34A", "red": "#DC2626", "amber": "#D97706"}
    return (
        f'<span class="badge badge-{color}">'
        f'<span class="badge-dot" style="background:{dots.get(color, "#000")}"></span>{label}</span>'
    )

def get_role_label(role):
    return {
        "agent_dp": "Agent DP",
        "admin_dp": "Administrateur DP",
        "admin_regional": "Administrateur Régional",
        "super_admin": "Super Administrateur",
    }.get(role, role)


def get_initials(name):
    parts = (name or "").strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper() if parts else "??"


def render_lot_detail_card(lot: dict, extra_info: dict = None):
    items = list(lot.items())
    if extra_info:
        items.extend(list(extra_info.items()))
    items_html = "".join(
        f'<div style="display:flex;flex-direction:column;gap:0.15rem;">'
        f'<span style="font-size:0.7rem;color:#6B7280;text-transform:uppercase;font-weight:600;">{k}</span>'
        f'<span style="color:#111827;font-weight:500;">{v}</span></div>'
        for k, v in items
    )
    return (
        f'<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;'
        f'padding:1rem 1.25rem;margin-bottom:1rem;">'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;font-size:0.82rem;">'
        f'{items_html}</div></div>'
    )


def render_prov_card(nom, total, pending, valides, rejetes):
    cc = (
        "background:#D1FAE5;color:#065F46;" if pending == 0
        else "background:#FEF3C7;color:#92400E;" if pending <= 3
        else "background:#EFF6FF;color:#1D4ED8;"
    )
    return (
        f'<div style="background:#FFF;border:1px solid #E5E7EB;border-radius:8px;padding:1rem;margin-bottom:0.75rem;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">'
        f'<div style="font-size:0.95rem;font-weight:600;">{nom}</div>'
        f'<div style="padding:0.2rem 0.55rem;border-radius:12px;font-size:0.72rem;font-weight:600;{cc}">{pending} en attente</div></div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;padding-top:0.6rem;border-top:1px solid #F3F4F6;">'
        f'<div style="text-align:center;"><div style="font-size:1.1rem;font-weight:700;">{total}</div>'
        f'<div style="font-size:0.68rem;color:#6B7280;">TOTAL</div></div>'
        f'<div style="text-align:center;"><div style="font-size:1.1rem;font-weight:700;color:#059669;">{valides}</div>'
        f'<div style="font-size:0.68rem;color:#6B7280;">VALIDÉS</div></div>'
        f'<div style="text-align:center;"><div style="font-size:1.1rem;font-weight:700;color:#DC2626;">{rejetes}</div>'
        f'<div style="font-size:0.68rem;color:#6B7280;">REJETÉS</div></div></div></div>'
    )


def get_chart_config():
    return {"displayModeBar": False, "displaylogo": False}


def apply_chart_theme(fig):
    fig.update_layout(
        font_family="Inter, sans-serif",
        font_color="#374151",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=11)),
        xaxis=dict(gridcolor="#F3F4F6", linecolor="#E5E7EB", tickfont=dict(size=11, color="#6B7280")),
        yaxis=dict(gridcolor="#F3F4F6", linecolor="#E5E7EB", tickfont=dict(size=11, color="#6B7280")),
    )
    return fig


CHART_COLORS = {
    "brouillon": "#94A3B8",
    "soumis": "#3B82F6",
    "valide_dp": "#F59E0B",
    "rejete_dp": "#EF4444",
    "valide_regional": "#10B981",
    "rejete_regional": "#DC2626",
}

STATUS_LABELS = {
    "brouillon": "Brouillon",
    "soumis": "Soumis",
    "valide_dp": "Validé DP",
    "rejete_dp": "Rejeté DP",
    "valide_regional": "Validé Régional",
    "rejete_regional": "Rejeté Régional",
    "en_cours_validation_dp": "En cours validation DP",
    "en_cours_validation_regional": "En cours validation Régional",
    "partiellement_rejete_dp": "Partiellement rejeté DP",
    "partiellement_rejete_regional": "Partiellement rejeté Régional",
    "modif_admin_dp": "En modification (Admin DP)",
    "modif_agent_dp": "En modification (Agent)",
    "en_modification_admin_dp": "En modification (Admin DP)",
    "en_modification_agent": "En modification (Agent)",
    "vide": "Vide",
    "en_cours_traitement": "En cours de traitement",
}