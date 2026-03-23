# main.py

import webview
import threading
import subprocess
import time
import urllib.request
import sys
import os

def start_streamlit():
    """Avvia il server Streamlit in background in modalità 'headless'"""
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "app.py")
    
    subprocess.Popen([
        python_exe, "-m", "streamlit", "run", script_path, 
        "--server.headless", "true",
        "--server.port", "8501"
    ])

def check_server():
    """Attende che il server sia pronto prima di mostrare la finestra"""
    while True:
        try:
            urllib.request.urlopen("http://localhost:8501")
            break
        except:
            time.sleep(0.5)

if __name__ == '__main__':
    print("⚡ Avvio di FiltroTool Pro (Architettura Ibrida Unificata)...")
    
    t = threading.Thread(target=start_streamlit)
    t.daemon = True
    t.start()
    
    print("Caricamento in corso...")
    check_server()
    
    print("Avvio Finestra Desktop...")
    window = webview.create_window(
        title='FiltroTool Pro - Sintesi Avanzata', 
        url='http://localhost:8501',
        width=1200, 
        height=850,
        background_color='#1A1A1D' 
    )
    
    webview.start()