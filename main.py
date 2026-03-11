import sys
from PyQt6.QtWidgets import QApplication
from gui.app_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Imposta lo stile nativo del sistema operativo (es. Windows, Fusion, macOS)
    app.setStyle("Fusion") 
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())