from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from gui.tabs import TabNorm, TabSynthesis, TabBode

# Importiamo il Design System centralizzato
from core.theme import Theme

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FiltroTool Pro - Sintesi Avanzata")
        self.resize(950, 750)
        
        # --- APPLICA IL TEMA GRAFICO UNIVERSALE ---
        self.setStyleSheet(Theme.get_pyqt_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("FiltroTool Pro")
        header.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {Theme.TEXT_PRIMARY}; background: transparent; border: none;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        subtitle = QLabel("Sintesi Avanzata Circuiti Passivi")
        subtitle.setStyleSheet(f"font-size: 14px; font-weight: 500; color: {Theme.ACCENT}; background: transparent; margin-bottom: 10px; border: none;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.tab_norm = TabNorm()
        self.tab_synthesis = TabSynthesis(self)
        self.tab_bode = TabBode()

        self.tabs.addTab(self.tab_norm, "De/Normalizzazione")
        self.tabs.addTab(self.tab_synthesis, "Sintesi Parametrica")
        self.tabs.addTab(self.tab_bode, "Analisi Bode")
        
        footer = QLabel("© Emanuele Negrino | Università di Genova")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: rgba(255,255,255,0.3); padding-top: 10px; font-size: 11px; background: transparent; border: none;")
        main_layout.addWidget(footer)

    def update_bode(self, filter_obj):
        self.tab_bode.plot_filter(filter_obj)
        self.tabs.setCurrentWidget(self.tab_bode)