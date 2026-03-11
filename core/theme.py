class Theme:
    """Design System Centralizzato - Stile Apple macOS / SwiftUI"""
    
    BG_GRADIENT_START = "#1A1A1D"
    BG_GRADIENT_END = "#000000"
    
    # Effetti Glassmorphism
    GLASS_BG = "rgba(44, 44, 46, 0.4)"
    GLASS_BORDER = "rgba(255, 255, 255, 0.15)"
    INPUT_BG = "rgba(0, 0, 0, 0.25)"
    
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#8E8E93"
    
    ACCENT = "#0A84FF"          # System Blue
    ACCENT_HOVER = "#4A9FFF"
    SUCCESS = "#32D74B"         # System Green
    DANGER = "#FF375F"          # System Red
    WARNING = "#FF9F0A"         # System Orange
    
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    FONT_CODE = "'Menlo', Consolas, monospace"
    RADIUS = "12px"
    
    @classmethod
    def get_pyqt_stylesheet(cls):
        return f"""
            QMainWindow, QWidget {{ font-family: {cls.FONT_FAMILY}; font-size: 13px; color: {cls.TEXT_PRIMARY}; }}
            QMainWindow {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {cls.BG_GRADIENT_START}, stop:1 {cls.BG_GRADIENT_END}); }}
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{ background: rgba(255, 255, 255, 0.05); color: {cls.TEXT_SECONDARY}; padding: 8px 24px; border-radius: 8px; margin: 4px 2px; font-weight: 600; font-size: 14px; }}
            QTabBar::tab:selected {{ background: rgba(255, 255, 255, 0.15); color: {cls.TEXT_PRIMARY}; border: 0.5px solid {cls.GLASS_BORDER}; }}
            QTabBar::tab:hover:!selected {{ background: rgba(255, 255, 255, 0.08); color: #D1D1D6; }}
            QGroupBox {{ background-color: {cls.GLASS_BG}; border: 1px solid {cls.GLASS_BORDER}; border-radius: {cls.RADIUS}; margin-top: 25px; padding-top: 20px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; top: 5px; color: {cls.TEXT_SECONDARY}; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
            QLineEdit, QComboBox, QTextEdit {{ background-color: {cls.INPUT_BG}; color: {cls.TEXT_PRIMARY}; border: 1px solid {cls.GLASS_BORDER}; padding: 8px 12px; border-radius: 8px; }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border: 1px solid {cls.ACCENT}; background-color: rgba(10, 132, 255, 0.05); }}
            QComboBox::drop-down {{ border: none; }}
            QRadioButton {{ color: {cls.TEXT_PRIMARY}; spacing: 10px; font-weight: 500; }}
            QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 9px; border: 1px solid #666666; background-color: rgba(0,0,0,0.3); }}
            QRadioButton::indicator:checked {{ border: 5px solid {cls.ACCENT}; background-color: {cls.BG_GRADIENT_START}; }}
            QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2C8CFF, stop:1 {cls.ACCENT}); color: white; font-weight: bold; font-size: 14px; padding: 10px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.3); }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {cls.ACCENT_HOVER}, stop:1 #1A8DFF); }}
            QPushButton:pressed {{ background: #005bb5; border: none; }}
        """

    @classmethod
    def get_streamlit_css(cls):
        return f"""
        <style>
            #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}} footer {{visibility: hidden;}}
            .block-container {{padding-top: 1rem; padding-bottom: 0rem;}}
            .stApp {{ background: linear-gradient(135deg, {cls.BG_GRADIENT_START}, {cls.BG_GRADIENT_END}); color: {cls.TEXT_PRIMARY}; font-family: {cls.FONT_FAMILY}; }}
            
            /* Segmented Control per i Tab */
            div[data-baseweb="tab_list"] {{ background-color: rgba(0,0,0,0.2); border-radius: 10px; padding: 5px; gap: 5px; }}
            div[data-baseweb="tab"] {{ background: transparent; border-radius: 8px; color: {cls.TEXT_SECONDARY} !important; border: none !important; }}
            div[aria-selected="true"] {{ background: rgba(255,255,255,0.15) !important; color: {cls.TEXT_PRIMARY} !important; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
            
            /* Glassmorphism reale con sfocatura hardware */
            [data-testid="stForm"], .stExpander {{ background-color: {cls.GLASS_BG} !important; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-radius: {cls.RADIUS} !important; border: 1px solid {cls.GLASS_BORDER} !important; }}
            .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {{ background-color: {cls.INPUT_BG}; color: {cls.TEXT_PRIMARY}; border: 1px solid {cls.GLASS_BORDER}; border-radius: 8px; transition: border 0.3s; }}
            .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {{ border: 1px solid {cls.ACCENT}; box-shadow: 0 0 5px {cls.ACCENT}; }}
            
            button[kind="primary"] {{ background: linear-gradient(180deg, #2C8CFF, {cls.ACCENT}) !important; border: 1px solid rgba(0,0,0,0.3) !important; color: white !important; border-radius: 10px !important; font-weight: bold !important; padding: 10px !important; transition: all 0.2s; }}
            button[kind="primary"]:hover {{ background: linear-gradient(180deg, {cls.ACCENT_HOVER}, #1A8DFF) !important; transform: translateY(-1px); box-shadow: 0 4px 10px rgba(10, 132, 255, 0.3); }}
            button[kind="secondary"] {{ background: {cls.GLASS_BG} !important; color: white !important; border: 1px solid {cls.GLASS_BORDER} !important; border-radius: 10px !important; }}
            
            p, label {{ color: {cls.TEXT_SECONDARY} !important; font-weight: 500 !important; }}
            h1, h2, h3, .stMarkdown p strong {{ color: {cls.TEXT_PRIMARY} !important; }}
            hr {{ border-color: {cls.GLASS_BORDER}; }}
        </style>
        """