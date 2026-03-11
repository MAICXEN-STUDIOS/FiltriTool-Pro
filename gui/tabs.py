from PyQt6.QtWidgets import (QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, 
                             QGroupBox, QRadioButton, QButtonGroup, QTabWidget, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import scipy.signal as signal
import math
from core.filter_logic import FilterSynthesizer

# --- UTILITIES ---
def format_eng(value, base_unit):
    if value == 0: return f"0.000 {base_unit}"
    degree = int(math.floor(math.log10(abs(value)) / 3))
    prefixes = { -4: 'p', -3: 'n', -2: 'µ', -1: 'm', 0: '', 1: 'k', 2: 'M', 3: 'G' }
    degree = max(min(degree, 3), -4)
    scaled_val = value * (1000 ** -degree)
    return f"{scaled_val:.3f} {prefixes[degree]}{base_unit}"

def get_nearest_E24(value):
    if value == 0: return 0
    E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 
           3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
    power = math.floor(math.log10(value))
    base = value / (10**power)
    closest_base = min(E24, key=lambda x: abs(x - base))
    return closest_base * (10**power)

def format_with_e24(val, base_unit):
    eng_val = format_eng(val, base_unit)
    e24_val = format_eng(get_nearest_E24(val), base_unit)
    return f"{eng_val}   <span style='color: #8E8E93; font-size: 14px; font-weight: normal;'>(E24: ~{e24_val})</span>"


# ==========================================
# TAB 1: NORMALIZZAZIONE (Identico al Web)
# ==========================================
class NormActionWidget(QWidget):
    def __init__(self, mode="norm"):
        super().__init__()
        self.mode = mode 
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        input_group = QGroupBox("Parametri di Riferimento")
        form_layout = QFormLayout()
        
        label_testo = "Valore Fisico Componente:" if mode == "norm" else "Valore Prototipo Normalizzato:"
        self.val_comp = QLineEdit("1")
        self.val_k = QLineEdit("1000")
        
        freq_layout = QHBoxLayout()
        self.val_freq = QLineEdit("1000")
        self.combo_freq_unit = QComboBox()
        self.combo_freq_unit.addItems(["rad/s", "Hz", "kHz", "MHz"])
        self.combo_freq_unit.setCurrentIndex(1)
        freq_layout.addWidget(self.val_freq)
        freq_layout.addWidget(self.combo_freq_unit)
        
        self.lbl_bw = QLabel("Banda (B) [stessa unità di f0]:")
        self.val_bw = QLineEdit("100")
        self.val_bw.hide()
        self.lbl_bw.hide()
        
        form_layout.addRow(label_testo, self.val_comp)
        form_layout.addRow("Fattore k (Resistenza di Carico):", self.val_k)
        form_layout.addRow("Frequenza Centrale (f0 / ω0):", freq_layout)
        form_layout.addRow(self.lbl_bw, self.val_bw)
        input_group.setLayout(form_layout)
        layout.addWidget(input_group)

        settings_layout = QHBoxLayout()
        
        type_group = QGroupBox("Trasformazione")
        v_type = QVBoxLayout()
        self.combo_op_type = QComboBox()
        self.combo_op_type.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_op_type.addItems(["Ampiezza e Frequenza", "Solo Ampiezza", "Solo Frequenza"])
        v_type.addWidget(self.combo_op_type)
        
        if self.mode == "denorm":
            self.combo_target_filter = QComboBox()
            self.combo_target_filter.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.combo_target_filter.addItems([
                "Passa-Basso (LP -> LP)", "Passa-Alto (LP -> HP)", 
                "Passa-Banda (LP -> BP)", "Elimina-Banda / Notch (LP -> BS)"
            ])
            self.combo_target_filter.currentIndexChanged.connect(self.update_ui_state)
            v_type.addWidget(self.combo_target_filter)
            
        type_group.setLayout(v_type)
        settings_layout.addWidget(type_group)

        comp_group = QGroupBox("Componente Originale")
        v_comp = QVBoxLayout()
        self.radio_group = QButtonGroup(self)
        for i, text in enumerate(["Resistore (R)", "Induttore (L)", "Condensatore (C)"]):
            rb = QRadioButton(text)
            rb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if i == 0: rb.setChecked(True)
            self.radio_group.addButton(rb, i)
            rb.toggled.connect(self.update_formula_display)
            v_comp.addWidget(rb)
        comp_group.setLayout(v_comp)
        settings_layout.addWidget(comp_group)
        layout.addLayout(settings_layout)

        self.lbl_formula = QLabel("Formule applicate: Seleziona parametri...")
        self.lbl_formula.setStyleSheet("font-family: 'Menlo', Consolas, monospace; font-size: 13px; color: rgba(255,255,255,0.6); padding: 5px;")
        self.lbl_formula.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_formula)

        btn_calc = QPushButton("Sintetizza Valore" if mode == "denorm" else "Calcola Normalizzazione")
        btn_calc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_calc.clicked.connect(self.calculate)
        layout.addWidget(btn_calc)

        self.val_comp.returnPressed.connect(self.calculate)
        self.val_k.returnPressed.connect(self.calculate)
        self.val_freq.returnPressed.connect(self.calculate)
        self.val_bw.returnPressed.connect(self.calculate)

        self.frame_risultato = QFrame()
        self.frame_risultato.setStyleSheet("""
            QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(60, 60, 67, 0.4), stop:1 rgba(44, 44, 46, 0.4));
                     border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
        """)
        res_layout = QVBoxLayout(self.frame_risultato)
        
        self.lbl_risultato = QLabel("In attesa di calcolo...")
        self.lbl_risultato.setStyleSheet("font-size: 18px; font-weight: 500; color: #8E8E93; background: transparent; border: none;")
        self.lbl_risultato.setAlignment(Qt.AlignmentFlag.AlignCenter)
        res_layout.addWidget(self.lbl_risultato)
        
        layout.addWidget(self.frame_risultato)
        layout.addStretch()

        self.combo_op_type.currentIndexChanged.connect(self.update_formula_display)
        self.update_ui_state()

    def update_ui_state(self):
        if self.mode == "denorm":
            idx = self.combo_target_filter.currentIndex()
            if idx in [2, 3] and self.combo_op_type.currentIndex() == 0:
                self.lbl_bw.show()
                self.val_bw.show()
            else:
                self.lbl_bw.hide()
                self.val_bw.hide()
        self.update_formula_display()
        if self.val_comp.text(): self.calculate()

    def update_formula_display(self):
        ctype = self.radio_group.checkedId()
        op_type = self.combo_op_type.currentIndex()
        formula = ""
        if self.mode == "norm":
            if op_type == 0: formula = "Rn = R/k" if ctype==0 else ("Ln = (L·ω0)/k" if ctype==1 else "Cn = C·k·ω0")
            elif op_type == 1: formula = "Rn = R/k" if ctype==0 else ("Ln = L/k" if ctype==1 else "Cn = C·k")
            elif op_type == 2: formula = "Rn = R" if ctype==0 else ("Ln = L·ω0" if ctype==1 else "Cn = C·ω0")
        else:
            filter_type = self.combo_target_filter.currentIndex()
            if op_type == 0: 
                if ctype == 0: formula = "R = Rn · k"
                elif filter_type == 0: formula = "L = (Ln·k)/ω0" if ctype==1 else "C = Cn/(k·ω0)"
                elif filter_type == 1: formula = "C = 1/(k·ω0·Ln) [L->C]" if ctype==1 else "L = k/(ω0·Cn) [C->L]"
                elif filter_type == 2: formula = "L_ser = (k·Ln)/B, C_ser = B/(k·ω0²·Ln)" if ctype==1 else "C_par = Cn/(k·B), L_par = (k·B)/(ω0²·Cn)"
                elif filter_type == 3: formula = "L_par = (k·B·Ln)/ω0², C_par = 1/(k·B·Ln)" if ctype==1 else "C_ser = (B·Cn)/(k·ω0²), L_ser = k/(B·Cn)"
            else:
                formula = "Richiesta scalatura Ampiezza+Frequenza."
        self.lbl_formula.setText(f"Modello:  {formula}")

    def get_w0_and_B(self):
        val_f = float(self.val_freq.text().replace(',', '.'))
        unit = self.combo_freq_unit.currentText()
        mult = 1.0
        if unit == "Hz": mult = 2 * math.pi
        elif unit == "kHz": mult = 2 * math.pi * 1e3
        elif unit == "MHz": mult = 2 * math.pi * 1e6
        return val_f * mult, float(self.val_bw.text().replace(',', '.')) * mult if self.val_bw.isVisible() else 1.0

    def calculate(self):
        try:
            val = float(self.val_comp.text().replace(',', '.'))
            k = float(self.val_k.text().replace(',', '.'))
            w0, B = self.get_w0_and_B()
            ctype = self.radio_group.checkedId() 
            op_type = self.combo_op_type.currentIndex() 
            
            if self.mode == "norm":
                res = 0.0
                unit = "Ω_n" if ctype == 0 else ("H_n" if ctype == 1 else "F_n")
                if op_type == 0: res = val/k if ctype==0 else ((w0*val)/k if ctype==1 else k*w0*val)
                elif op_type == 1: res = val/k if ctype==0 else (val/k if ctype==1 else k*val)
                elif op_type == 2: res = val if ctype==0 else (w0*val if ctype==1 else w0*val)
                self.lbl_risultato.setText(f"{format_eng(res, unit)}")
                self.lbl_risultato.setStyleSheet("font-size: 28px; font-weight: 700; color: #32D74B; background: transparent; border: none;")
            else: 
                filter_type = self.combo_target_filter.currentIndex()
                if op_type == 0: 
                    if ctype == 0:
                        self.lbl_risultato.setText(format_with_e24(k * val, 'Ω'))
                        self.lbl_risultato.setStyleSheet("color: #32D74B; font-size: 24px; font-weight: bold; background: transparent; border: none;")
                    elif filter_type == 0: 
                        res_str = format_with_e24((k * val) / w0, 'H') if ctype == 1 else format_with_e24(val / (w0 * k), 'F')
                        self.lbl_risultato.setText(res_str)
                        self.lbl_risultato.setStyleSheet("color: #32D74B; font-size: 24px; font-weight: bold; background: transparent; border: none;")
                    elif filter_type == 1: 
                        if ctype == 1: res_str = format_with_e24(1.0 / (k * w0 * val), 'F') + "<br><span style='font-size: 14px; font-weight: normal; color:#FF9F0A;'>(Convertito da Induttore a Condensatore)</span>"
                        elif ctype == 2: res_str = format_with_e24(k / (w0 * val), 'H') + "<br><span style='font-size: 14px; font-weight: normal; color:#FF9F0A;'>(Convertito da Condensatore a Induttore)</span>"
                        self.lbl_risultato.setText(res_str)
                        self.lbl_risultato.setStyleSheet("color: #FFD60A; font-size: 24px; font-weight: bold; background: transparent; border: none;")
                    elif filter_type == 2: 
                        if ctype == 1: res_str = f"Ramo Serie LC:<br><span style='color: #0A84FF;'>L_s = {format_with_e24((k * val) / B, 'H')}</span><br><span style='color: #FF375F;'>C_s = {format_with_e24(B / (k * (w0**2) * val), 'F')}</span>"
                        elif ctype == 2: res_str = f"Ramo Parallelo LC:<br><span style='color: #FF375F;'>C_p = {format_with_e24(val / (k * B), 'F')}</span><br><span style='color: #0A84FF;'>L_p = {format_with_e24((k * B) / ((w0**2) * val), 'H')}</span>"
                        self.lbl_risultato.setText(res_str)
                        self.lbl_risultato.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: bold; background: transparent; border: none;")
                    elif filter_type == 3: 
                        if ctype == 1: res_str = f"Ramo Parallelo LC:<br><span style='color: #0A84FF;'>L_p = {format_with_e24((k * B * val) / (w0**2), 'H')}</span><br><span style='color: #FF375F;'>C_p = {format_with_e24(1.0 / (k * B * val), 'F')}</span>"
                        elif ctype == 2: res_str = f"Ramo Serie LC:<br><span style='color: #FF375F;'>C_s = {format_with_e24((B * val) / (k * (w0**2)), 'F')}</span><br><span style='color: #0A84FF;'>L_s = {format_with_e24(k / (B * val), 'H')}</span>"
                        self.lbl_risultato.setText(res_str)
                        self.lbl_risultato.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: bold; background: transparent; border: none;")
                elif op_type == 1: 
                    if ctype == 0: res_str = format_with_e24(k * val, 'Ω')
                    elif ctype == 1: res_str = format_with_e24(k * val, 'H')
                    elif ctype == 2: res_str = format_with_e24(val / k, 'F')
                    self.lbl_risultato.setText(res_str)
                    self.lbl_risultato.setStyleSheet("color: #32D74B; font-size: 24px; font-weight: bold; background: transparent; border: none;")
                elif op_type == 2: 
                    if ctype == 0: res_str = format_with_e24(val, 'Ω')
                    elif ctype == 1: res_str = format_with_e24(val / w0, 'H')
                    elif ctype == 2: res_str = format_with_e24(val / w0, 'F')
                    self.lbl_risultato.setText(res_str)
                    self.lbl_risultato.setStyleSheet("color: #32D74B; font-size: 24px; font-weight: bold; background: transparent; border: none;")

        except ValueError:
            self.lbl_risultato.setText("Errore: Verifica i dati di input")
            self.lbl_risultato.setStyleSheet("color: #FF453A; font-size: 16px; background: transparent; border: none;")
        except ZeroDivisionError:
            self.lbl_risultato.setText("Errore: Divisione per zero")
            self.lbl_risultato.setStyleSheet("color: #FF453A; font-size: 16px; background: transparent; border: none;")

class TabNorm(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.tab_normalize = NormActionWidget(mode="norm")
        self.tab_denormalize = NormActionWidget(mode="denorm")
        self.sub_tabs.addTab(self.tab_normalize, "Normalizzazione Fisica")
        self.sub_tabs.addTab(self.tab_denormalize, "Denormalizzazione Fisica")
        layout.addWidget(self.sub_tabs)


# ==========================================
# TAB 2: SINTESI E CIRCUITO CAD
# ==========================================
class TabSynthesis(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)
        
        ctrl_layout = QHBoxLayout()
        
        # --- COLONNA 1: ARCHITETTURA ---
        group_type = QGroupBox("Architettura di Rete")
        fl_type = QFormLayout()
        self.cb_approx = QComboBox()
        self.cb_approx.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cb_approx.addItems(["Butterworth", "Chebyshev", "Bessel (Solo Bode)"])
        self.cb_resp = QComboBox()
        self.cb_resp.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cb_resp.addItems(["Low-Pass (LP)", "High-Pass (HP)", "Band-Pass (BP)", "Band-Stop/Notch (BS)"])
        self.cb_resp.currentIndexChanged.connect(self.update_labels)
        fl_type.addRow("Famiglia:", self.cb_approx)
        fl_type.addRow("Risposta:", self.cb_resp)
        group_type.setLayout(fl_type)
        ctrl_layout.addWidget(group_type)

        # --- COLONNA 2: TOPOLOGIA ---
        group_topo = QGroupBox("Topologia e Sintesi")
        fl_topo = QFormLayout()
        self.cb_spec = QComboBox()
        self.cb_spec.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cb_spec.addItems(["Sovraspecifica Banda Oscura (Match Ap)", "Sovraspecifica Banda Passante (Match As)"])
        self.cb_first = QComboBox()
        self.cb_first.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cb_first.addItems(["Inizia con Induttore Serie (L)", "Inizia con Condensatore Shunt (C)"])
        fl_topo.addRow("Ottimizzazione:", self.cb_spec)
        fl_topo.addRow("Cella d'Ingresso:", self.cb_first)
        group_topo.setLayout(fl_topo)
        ctrl_layout.addWidget(group_topo)
        
        # --- COLONNA 3: SPECIFICHE NUMERICHE ---
        group_spec = QGroupBox("Specifiche (Hz, dB, Ω)")
        self.fl_spec = QFormLayout() # <--- FIXED BUG QUI: Aggiunto self.
        self.entries = {}
        
        self.lbl_fcenter = QLabel("Frequenza Centrale f0 (Hz):")
        self.ent_fcenter = QLineEdit("1000")
        self.ent_fcenter.returnPressed.connect(self.run_synthesis)
        self.fl_spec.addRow(self.lbl_fcenter, self.ent_fcenter)
        self.lbl_fcenter.hide(); self.ent_fcenter.hide()
        
        for label, default in [("fp (Hz):", "1000"), ("fs (Hz):", "5000"), ("αp (dB):", "1"), ("αs (dB):", "40"), ("R_load (Ω):", "50")]:
            le = QLineEdit(default)
            # Live update per il grafico della maschera
            le.textChanged.connect(self.update_mask_plot)
            le.returnPressed.connect(self.run_synthesis)
            lbl = QLabel(label)
            self.fl_spec.addRow(lbl, le)
            self.entries[label] = {"label": lbl, "entry": le}
            
        group_spec.setLayout(self.fl_spec)
        ctrl_layout.addWidget(group_spec)
        
        # --- COLONNA 4: MASCHERA DIDATTICA ---
        group_mask = QGroupBox("Maschera Attenuazione")
        mask_layout = QVBoxLayout()
        self.fig_mask, self.ax_mask = plt.subplots(figsize=(3.5, 2.5))
        self.fig_mask.patch.set_facecolor('none')
        self.ax_mask.set_facecolor('none')
        self.canvas_mask = FigureCanvas(self.fig_mask)
        self.canvas_mask.setStyleSheet("background: transparent;")
        mask_layout.addWidget(self.canvas_mask)
        group_mask.setLayout(mask_layout)
        ctrl_layout.addWidget(group_mask)
        
        layout.addLayout(ctrl_layout)
        
        # --- BOTTONE DI CALCOLO ---
        btn_calc = QPushButton("Genera Schematico e Circuito a Scala (Cauer)")
        btn_calc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_calc.clicked.connect(self.run_synthesis)
        layout.addWidget(btn_calc)

        # --- PANNELLO INFERIORE (LOG + CIRCUITO) ---
        bottom_layout = QHBoxLayout()
        
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setMaximumWidth(320)
        self.text_log.setStyleSheet("font-family: 'Menlo', Consolas, monospace; font-size: 11px; background: rgba(0,0,0,0.3); color: #32D74B; border-radius: 8px; padding: 8px;")
        bottom_layout.addWidget(self.text_log)

        self.fig_circ, self.ax_circ = plt.subplots(figsize=(6, 3))
        self.fig_circ.patch.set_facecolor('#1c1c1e')
        self.ax_circ.set_facecolor('#1c1c1e')
        self.ax_circ.axis('off')
        self.canvas_circ = FigureCanvas(self.fig_circ)
        self.canvas_circ.setStyleSheet("background: transparent; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);")
        bottom_layout.addWidget(self.canvas_circ)
        
        layout.addLayout(bottom_layout)
        
        self.entries["fp (Hz):"]["entry"].setFocus()
        self.update_mask_plot()

    def update_mask_plot(self):
        """Disegna in tempo reale la maschera didattica del filtro"""
        try:
            fp = float(self.entries["fp (Hz):"]["entry"].text())
            fs = float(self.entries["fs (Hz):"]["entry"].text())
            ap = float(self.entries["αp (dB):"]["entry"].text())
            As = float(self.entries["αs (dB):"]["entry"].text())
            f_center = float(self.ent_fcenter.text())
            
            resp = self.cb_resp.currentText()
            r_code = "LP" if "LP" in resp else ("HP" if "HP" in resp else ("BP" if "BP" in resp else "BS"))
            
            self.ax_mask.clear()
            self.ax_mask.invert_yaxis()
            max_a = max(As * 1.2, 60)
            
            color_pass = (50/255, 215/255, 75/255, 0.2) 
            color_stop = (255/255, 55/255, 95/255, 0.2) 
            txt_col = '#FFFFFF'
            
            def mark_point(x, y, label, ha='left', va='bottom', offset_x=1.1, offset_y=-2):
                self.ax_mask.plot(x, y, 'o', color='white', markersize=4)
                self.ax_mask.text(x * offset_x, y + offset_y, label, color=txt_col, ha=ha, va=va, fontsize=8, fontweight='bold')

            if r_code == "LP":
                self.ax_mask.fill_between([1e-5, fp], 0, ap, color=color_pass, lw=0)
                self.ax_mask.fill_between([fs, 1e7], As, max_a, color=color_stop, lw=0)
                self.ax_mask.plot([1e-5, fp, fs, 1e7], [0, ap, As, As], color='gray', lw=1.5, ls='--')
                mark_point(fp, ap, "fp, αp", ha='right', offset_x=0.9)
                mark_point(fs, As, "fs, αs", ha='left', offset_x=1.1, offset_y=3)
                self.ax_mask.set_xlim(max(1, fp/10), fs*10)

            elif r_code == "HP":
                self.ax_mask.fill_between([1e-5, fs], As, max_a, color=color_stop, lw=0)
                self.ax_mask.fill_between([fp, 1e7], 0, ap, color=color_pass, lw=0)
                self.ax_mask.plot([1e-5, fs, fp, 1e7], [As, As, ap, 0], color='gray', lw=1.5, ls='--')
                mark_point(fs, As, "fs, αs", ha='right', offset_x=0.9, offset_y=3)
                mark_point(fp, ap, "fp, αp", ha='left', offset_x=1.1)
                self.ax_mask.set_xlim(max(1, fs/10), fp*10)

            elif r_code in ["BP", "BS"]:
                Bp, Bs = fp, fs 
                f0 = f_center
                fp1 = (-Bp + math.sqrt(Bp**2 + 4*f0**2))/2; fp2 = fp1 + Bp
                fs1 = (-Bs + math.sqrt(Bs**2 + 4*f0**2))/2; fs2 = fs1 + Bs
                
                if r_code == "BP":
                    self.ax_mask.fill_between([1e-5, fs1], As, max_a, color=color_stop, lw=0)
                    self.ax_mask.fill_between([fp1, fp2], 0, ap, color=color_pass, lw=0)
                    self.ax_mask.fill_between([fs2, 1e7], As, max_a, color=color_stop, lw=0)
                    self.ax_mask.plot([1e-5, fs1, fp1, fp2, fs2, 1e7], [As, As, ap, ap, As, As], color='gray', lw=1.5, ls='--')
                    mark_point(fp1, ap, "fp1", ha='right', offset_x=0.9)
                    mark_point(fp2, ap, "fp2", ha='left', offset_x=1.1)
                    
                    self.ax_mask.annotate('', xy=(fp1, ap/2), xytext=(fp2, ap/2), arrowprops=dict(arrowstyle='<->', color='white'))
                    self.ax_mask.text(f0, ap/2 - 2, "B_pass", color='white', ha='center', fontsize=8)
                    self.ax_mask.set_xlim(fs1/2, fs2*2)
                    
                else: # BS
                    self.ax_mask.fill_between([1e-5, fp1], 0, ap, color=color_pass, lw=0)
                    self.ax_mask.fill_between([fs1, fs2], As, max_a, color=color_stop, lw=0)
                    self.ax_mask.fill_between([fp2, 1e7], 0, ap, color=color_pass, lw=0)
                    self.ax_mask.plot([1e-5, fp1, fs1, fs2, fp2, 1e7], [0, ap, As, As, ap, 0], color='gray', lw=1.5, ls='--')
                    mark_point(fs1, As, "fs1", ha='right', offset_x=0.9, offset_y=3)
                    mark_point(fs2, As, "fs2", ha='left', offset_x=1.1, offset_y=3)
                    
                    self.ax_mask.annotate('', xy=(fs1, As-5), xytext=(fs2, As-5), arrowprops=dict(arrowstyle='<->', color='white'))
                    self.ax_mask.text(f0, As-8, "B_stop", color='white', ha='center', fontsize=8)
                    self.ax_mask.set_xlim(fp1/2, fp2*2)
                
            self.ax_mask.set_xscale('log')
            self.ax_mask.set_ylim(max_a, -2)
            self.ax_mask.tick_params(colors='#8E8E93', labelsize=8)
            for spine in self.ax_mask.spines.values(): spine.set_color('none')
            self.ax_mask.grid(True, which="both", ls="-", color="white", alpha=0.05)
            self.canvas_mask.draw()
        except:
            pass

    def update_labels(self):
        resp = self.cb_resp.currentText()
        if "BP" in resp or "BS" in resp:
            self.lbl_fcenter.show(); self.ent_fcenter.show()
            self.entries["fp (Hz):"]["label"].setText("Banda Passante Bp (Hz):")
            self.entries["fs (Hz):"]["label"].setText("Banda Oscura Bs (Hz):")
        else:
            self.lbl_fcenter.hide(); self.ent_fcenter.hide()
            self.entries["fp (Hz):"]["label"].setText("fp (Hz):")
            self.entries["fs (Hz):"]["label"].setText("fs (Hz):")
            
        self.update_mask_plot()
        if self.entries["fp (Hz):"]["entry"].text():
            self.run_synthesis()

    def run_synthesis(self):
        try:
            fp = float(self.entries["fp (Hz):"]["entry"].text())
            fs = float(self.entries["fs (Hz):"]["entry"].text())
            ap = float(self.entries["αp (dB):"]["entry"].text())
            As = float(self.entries["αs (dB):"]["entry"].text())
            R_load = float(self.entries["R_load (Ω):"]["entry"].text())
            f_center = float(self.ent_fcenter.text())
            
            filt_type = self.cb_approx.currentText().split()[0]
            resp_raw = self.cb_resp.currentText()
            if "LP" in resp_raw: resp_type = "LP"
            elif "HP" in resp_raw: resp_type = "HP"
            elif "BP" in resp_raw: resp_type = "BP"
            else: resp_type = "BS"
            
            spec_type = "pass" if "Oscura" in self.cb_spec.currentText() else "stop"
            first_elem = "L" if "Induttore" in self.cb_first.currentText() else "C"
            
            filtro = FilterSynthesizer(filt_type, resp_type, spec_type, fp, fs, ap, As, R_load, first_elem, f_center)
            res = filtro.synthesize()
            
            log = f"=== SINTESI {filt_type[:3].upper()} {resp_type} ===\nOrdine (N): {res['N']}\n"
            if resp_type in ["LP", "HP"]: log += f"Taglio reale: {res['f0']:.1f} Hz\n"
            else: log += f"Banda reale: {res['B0']:.1f} Hz\n"
            
            log += "--------------------\nBOM (Componenti Reali):\n"
            for c in res['network']:
                if 'val_L' in c: 
                    val_L = format_with_e24(c['val_L'], 'H').replace("<span style='color: #8E8E93; font-size: 14px; font-weight: normal;'>", "").replace("</span>", "")
                    val_C = format_with_e24(c['val_C'], 'F').replace("<span style='color: #8E8E93; font-size: 14px; font-weight: normal;'>", "").replace("</span>", "")
                    log += f" <b>{c['type']}</b>:\n  L: {val_L}\n  C: {val_C}\n"
                else: 
                    unit = "H" if "L" in c['type'] else "F"
                    val_str = format_with_e24(c['val'], unit).replace("<span style='color: #8E8E93; font-size: 14px; font-weight: normal;'>", "").replace("</span>", "")
                    log += f" <b>{c['type']}</b>:\n  {val_str}\n"
                
            self.text_log.setHtml(log.replace('\n', '<br>'))
            self.draw_circuit(res['network'], R_load)
            self.main_window.update_bode(filtro)
            self.update_mask_plot()
            
        except Exception as e:
            self.text_log.setText(f"Errore: {str(e)}")

    def draw_circuit(self, network, R_load):
        self.ax_circ.clear()
        self.ax_circ.axis('off')
        x, y_top, y_bot = 0, 1, 0
        
        self.ax_circ.plot([x, x+0.2], [y_top, y_top], color='white', lw=2)
        self.ax_circ.plot([x, x+0.2], [y_bot, y_bot], color='white', lw=2)
        self.ax_circ.text(x-0.1, 0.5, "IN", color='white', ha='right', va='center', fontweight='bold', fontsize=12)
        x += 0.2
        
        for comp in network:
            ctype = comp['type']
            label_id = "Cell_" + str(comp['id'])
            
            def draw_L(xi, yi, rot='h', col='#FF9F0A'):
                t = np.linspace(0, 4*np.pi, 100)
                if rot == 'h': self.ax_circ.plot(np.linspace(xi, xi+0.4, 100), yi + 0.12*np.abs(np.sin(t)), color=col, lw=2.5)
                else: self.ax_circ.plot(xi + 0.12*np.abs(np.sin(t)), np.linspace(yi, yi-0.4, 100), color=col, lw=2.5)
                
            def draw_C(xi, yi, rot='h', col='#0A84FF'):
                if rot == 'h':
                    self.ax_circ.plot([xi, xi+0.15], [yi, yi], color='white', lw=2)
                    self.ax_circ.plot([xi+0.25, xi+0.4], [yi, yi], color='white', lw=2)
                    self.ax_circ.plot([xi+0.15, xi+0.15], [yi-0.2, yi+0.2], color=col, lw=2.5)
                    self.ax_circ.plot([xi+0.25, xi+0.25], [yi-0.2, yi+0.2], color=col, lw=2.5)
                else:
                    self.ax_circ.plot([xi, xi], [yi, yi-0.15], color='white', lw=2)
                    self.ax_circ.plot([xi, xi], [yi-0.25, yi-0.4], color='white', lw=2)
                    self.ax_circ.plot([xi-0.2, xi+0.2], [yi-0.15, yi-0.15], color=col, lw=2.5)
                    self.ax_circ.plot([xi-0.2, xi+0.2], [yi-0.25, yi-0.25], color=col, lw=2.5)

            if ctype in ["L_series", "C_series"]: 
                self.ax_circ.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
                self.ax_circ.plot([x, x+0.2], [y_top, y_top], color='white', lw=2)
                self.ax_circ.plot([x+0.6, x+0.8], [y_top, y_top], color='white', lw=2)
                if 'L' in ctype: draw_L(x+0.2, y_top, 'h')
                else: draw_C(x+0.2, y_top, 'h')
                self.ax_circ.text(x+0.4, y_top+0.3, format_eng(comp['val'], 'H' if 'L' in ctype else 'F'), color='white', ha='center', fontsize=8)
                x += 0.8

            elif ctype in ["L_shunt", "C_shunt"]:
                self.ax_circ.plot([x, x+0.8], [y_top, y_top], color='white', lw=2)
                self.ax_circ.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
                self.ax_circ.plot([x+0.4, x+0.4], [y_top, y_top-0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.4, x+0.4], [y_bot+0.3, y_bot], color='white', lw=2)
                if 'L' in ctype: draw_L(x+0.4, y_top-0.3, 'v')
                else: draw_C(x+0.4, y_top-0.3, 'v')
                self.ax_circ.text(x+0.6, 0.5, format_eng(comp['val'], 'H' if 'L' in ctype else 'F'), color='white', va='center', fontsize=8)
                x += 0.8
                
            elif ctype == "LC_series_series": 
                self.ax_circ.plot([x, x+1.2], [y_bot, y_bot], color='white', lw=2)
                self.ax_circ.plot([x, x+0.1], [y_top, y_top], color='white', lw=2)
                draw_L(x+0.1, y_top, 'h')
                self.ax_circ.plot([x+0.5, x+0.7], [y_top, y_top], color='white', lw=2)
                draw_C(x+0.7, y_top, 'h')
                self.ax_circ.plot([x+1.1, x+1.2], [y_top, y_top], color='white', lw=2)
                x += 1.2
                
            elif ctype == "LC_shunt_parallel":
                self.ax_circ.plot([x, x+1.0], [y_top, y_top], color='white', lw=2)
                self.ax_circ.plot([x, x+1.0], [y_bot, y_bot], color='white', lw=2)
                self.ax_circ.plot([x+0.5, x+0.5], [y_top, y_top-0.1], color='white', lw=2)
                self.ax_circ.plot([x+0.5, x+0.5], [y_bot+0.1, y_bot], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.8], [y_top-0.1, y_top-0.1], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.8], [y_bot+0.1, y_bot+0.1], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.2], [y_top-0.1, y_top-0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.2], [y_bot+0.3, y_bot+0.1], color='white', lw=2)
                self.ax_circ.plot([x+0.8, x+0.8], [y_top-0.1, y_top-0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.8, x+0.8], [y_bot+0.3, y_bot+0.1], color='white', lw=2)
                draw_C(x+0.2, y_top-0.3, 'v')
                draw_L(x+0.8, y_top-0.3, 'v')
                x += 1.0
                
            elif ctype == "LC_series_parallel": 
                self.ax_circ.plot([x, x+1.2], [y_bot, y_bot], color='white', lw=2)
                self.ax_circ.plot([x, x+0.2], [y_top, y_top], color='white', lw=2)
                self.ax_circ.plot([x+1.0, x+1.2], [y_top, y_top], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.2], [y_top-0.3, y_top+0.3], color='white', lw=2)
                self.ax_circ.plot([x+1.0, x+1.0], [y_top-0.3, y_top+0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.4], [y_top+0.3, y_top+0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.8, x+1.0], [y_top+0.3, y_top+0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.2, x+0.4], [y_top-0.3, y_top-0.3], color='white', lw=2)
                self.ax_circ.plot([x+0.8, x+1.0], [y_top-0.3, y_top-0.3], color='white', lw=2)
                draw_L(x+0.4, y_top+0.3, 'h')
                draw_C(x+0.4, y_top-0.3, 'h')
                x += 1.2
                
            elif ctype == "LC_shunt_series":
                self.ax_circ.plot([x, x+0.8], [y_top, y_top], color='white', lw=2)
                self.ax_circ.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
                self.ax_circ.plot([x+0.4, x+0.4], [y_top, y_top-0.1], color='white', lw=2)
                draw_C(x+0.4, y_top-0.1, 'v')
                self.ax_circ.plot([x+0.4, x+0.4], [y_top-0.5, y_top-0.6], color='white', lw=2)
                draw_L(x+0.4, y_top-0.6, 'v')
                self.ax_circ.plot([x+0.4, x+0.4], [y_bot+0.1, y_bot], color='white', lw=2)
                x += 0.8
                
        self.ax_circ.plot([x, x+0.4], [y_top, y_top], color='white', lw=2)
        self.ax_circ.plot([x, x+0.4], [y_bot, y_bot], color='white', lw=2)
        self.ax_circ.plot([x+0.4, x+0.4], [y_top, y_top-0.3], color='white', lw=2)
        self.ax_circ.plot([x+0.4, x+0.4], [y_bot+0.3, y_bot], color='white', lw=2)

        y_zig = np.linspace(y_top-0.3, y_bot+0.3, 7)
        x_zig = x+0.4 + np.array([0, 0.15, -0.15, 0.15, -0.15, 0.15, 0])
        self.ax_circ.plot(x_zig, y_zig, color='#32D74B', lw=2.5)
        self.ax_circ.text(x+0.65, 0.5, f"RL\n{R_load}Ω", color='#32D74B', va='center', fontweight='bold', fontsize=10)

        self.ax_circ.plot([x+0.4, x+0.6], [y_top, y_top], color='white', lw=2)
        self.ax_circ.plot([x+0.4, x+0.6], [y_bot, y_bot], color='white', lw=2)
        self.ax_circ.plot(x+0.6, y_top, 'o', markeredgecolor='white', markerfacecolor='#1c1c1e', ms=6)
        self.ax_circ.plot(x+0.6, y_bot, 'o', markeredgecolor='white', markerfacecolor='#1c1c1e', ms=6)
        self.ax_circ.text(x+0.75, 0.5, "OUT", color='white', ha='left', va='center', fontweight='bold', fontsize=12)
        
        self.ax_circ.set_xlim(-0.5, x+1.2)
        self.ax_circ.set_ylim(-0.8, 1.8)
        self.canvas_circ.draw()

# ==========================================
# TAB 3: BODE
# ==========================================
class TabBode(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        ctrl_layout = QHBoxLayout()
        self.cb_plot_type = QComboBox()
        self.cb_plot_type.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cb_plot_type.addItems([
            "|H(jω)| e Fase (Lineare)", "10·log|H(jω)| e Fase (Potenza)",
            "Guadagno: 20·log|H(jω)| e Fase", "Attenuazione: -20·log|H(jω)| e Fase"
        ])
        ctrl_layout.addWidget(QLabel("Metrica d'Ampiezza:"))
        ctrl_layout.addWidget(self.cb_plot_type)
        
        self.cb_scale = QComboBox()
        self.cb_scale.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cb_scale.addItems(["Semilogaritmica (X-Log, Y-Lin)", "Bilogaritmica (X-Log, Y-Log)", "Lineare"])
        ctrl_layout.addWidget(QLabel("Scala Assi:"))
        ctrl_layout.addWidget(self.cb_scale)
        
        self.cb_plot_type.currentIndexChanged.connect(self.force_redraw)
        self.cb_scale.currentIndexChanged.connect(self.force_redraw)
        layout.addLayout(ctrl_layout)
        
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.fig.patch.set_facecolor('#1c1c1e')
        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background: transparent; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);")
        layout.addWidget(self.canvas)
        self.last_filter = None

    def plot_filter(self, filter_obj):
        self.last_filter = filter_obj
        self.force_redraw()

    def force_redraw(self):
        if not self.last_filter: return
        self.fig.clf() 
        try:
            b, a = self.last_filter.get_transfer_function()
            if self.last_filter.response_type in ["LP", "HP"]: f_ref = self.last_filter.f0
            else: f_ref = self.last_filter.f_center
            if f_ref <= 0: f_ref = 1000 
            
            w, h = signal.freqs(b, a, worN=np.logspace(np.log10(f_ref/100), np.log10(f_ref*100), 1000))
            f = w / (2 * np.pi)
            
            mag_linear = abs(h)
            mag_linear[mag_linear == 0] = np.finfo(float).eps 
            phase_rad = np.unwrap(np.angle(h))
            
            plot_type = self.cb_plot_type.currentIndex()
            scale_type = self.cb_scale.currentIndex()
            
            if plot_type == 0: y_mag, y_label, mag_color = mag_linear, '|H(jω)|', '#32D74B' 
            elif plot_type == 1: y_mag, y_label, mag_color = 10 * np.log10(mag_linear), '10·log|H(jω)| [dB]', '#0A84FF' 
            elif plot_type == 2: y_mag, y_label, mag_color = 20 * np.log10(mag_linear), 'Guadagno 20·log|H(jω)| [dB]', '#0A84FF' 
            else: y_mag, y_label, mag_color = -20 * np.log10(mag_linear), 'Attenuazione -20·log|H(jω)| [dB]', '#FF9F0A' 
            
            ax_mag = self.fig.add_subplot(211)
            ax_pha = self.fig.add_subplot(212)
            
            ax_mag.plot(f, y_mag, color=mag_color, lw=2.5)
            ax_mag.set_ylabel(y_label, color="#8E8E93", fontweight='bold')
            ax_mag.set_title(f"Diagramma di Bode - {self.last_filter.filter_type} {self.last_filter.response_type}", color="white", fontweight='bold')
            
            ax_pha.plot(f, phase_rad, color='#FF375F', lw=2.5)
            ax_pha.set_ylabel('Fase ∠H(jω) [rad]', color="#8E8E93", fontweight='bold')
            ax_pha.set_xlabel('Frequenza [Hz]', color="#8E8E93", fontweight='bold')
            
            axes = [ax_mag, ax_pha]
            for ax in axes:
                ax.set_facecolor('#1c1c1e')
                ax.grid(True, which="both", ls="-", color="white", alpha=0.1)
                for spine in ax.spines.values(): spine.set_color('none')
                ax.tick_params(colors="#8E8E93")
                if scale_type == 0: ax.set_xscale('log') 
                elif scale_type == 1: 
                    ax.set_xscale('log')
                    if ax == ax_mag and plot_type == 0: ax.set_yscale('log') 
                    elif ax == ax_mag: ax.set_yscale('symlog') 
                
            self.fig.tight_layout(pad=2.0)
            self.canvas.draw()
        except Exception as e:
            print(f"Errore plotting Bode: {e}")