import streamlit as st
import matplotlib.pyplot as plt
import math
from core.filter_logic import FilterSynthesizer
from core.theme import Theme
from core.shared_graphics import format_eng, format_with_e24, draw_tolerance_mask, draw_circuit, draw_bode

# --- AUTENTICAZIONE IBRIDA ---
try:
    WHITELIST_EMAILS = st.secrets["WHITELIST_EMAILS"]
    PASSWORD_CORRETTA = st.secrets["PASSWORD_CORRETTA"]
except FileNotFoundError:
    try:
        from core.whitelist import WHITELIST_EMAILS, PASSWORD_CORRETTA
    except ImportError:
        WHITELIST_EMAILS = []
        PASSWORD_CORRETTA = ""

st.set_page_config(page_title="FiltroTool Pro", page_icon="⚡", layout="wide")
st.markdown(Theme.get_streamlit_css(), unsafe_allow_html=True)

if 'autenticato' not in st.session_state: st.session_state['autenticato'] = False
if not st.session_state['autenticato']:
    st.markdown(f"<h1 style='text-align: center;'>🔒 FiltroTool Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email Unige:")
            password = st.text_input("Password:", type="password")
            if st.form_submit_button("Accedi", type="primary"):
                if email in WHITELIST_EMAILS and password == PASSWORD_CORRETTA: st.session_state['autenticato'] = True; st.rerun()
                else: st.error("Accesso negato.")
    st.stop()

st.markdown(f"<h1 style='text-align: center;'>FiltroTool Pro</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {Theme.ACCENT}; font-weight: bold;'>Sintesi Avanzata Circuiti Passivi</p>", unsafe_allow_html=True)

tab_norm, tab_sintesi, tab_bode = st.tabs(["⚖️ De/Normalizzazione", "🎛️ Sintesi Parametrica", "📈 Analisi Bode"])

# ==========================================
# TAB 1: DE/NORMALIZZAZIONE UNIVERSALE
# ==========================================
with tab_norm:
    mode = st.radio("Seleziona Operazione:", ["Normalizzazione Fisica", "Denormalizzazione Fisica"], horizontal=True)
    
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            val_comp = st.number_input("Valore Componente (Fisico o Normalizzato):", value=1.0, format="%.6g")
            k_val = st.number_input("Fattore k (Resistenza Carico):", value=1000.0)
            cc1, cc2 = st.columns([2,1])
            with cc1: val_freq = st.number_input("Frequenza (f0 / ω0):", value=1000.0)
            with cc2: unit_freq = st.selectbox("Unità:", ["Hz", "kHz", "MHz", "rad/s"])
            mult = 2 * math.pi if "Hz" in unit_freq else 1.0
            if unit_freq == "kHz": mult *= 1e3; 
            if unit_freq == "MHz": mult *= 1e6
            w0 = val_freq * mult

        with c2:
            op_type = st.selectbox("Trasformazione:", ["Ampiezza e Frequenza", "Solo Ampiezza", "Solo Frequenza"])
            ctype = st.selectbox("Componente Originale:", ["Resistore (R)", "Induttore (L)", "Condensatore (C)"])
            B = 1.0
            if "Denorm" in mode:
                target_filter = st.selectbox("Architettura Target:", ["Passa-Basso (LP)", "Passa-Alto (HP)", "Passa-Banda (BP)", "Elimina-Banda (BS)"])
                if "BP" in target_filter or "BS" in target_filter: B = st.number_input("Banda (B) [stessa unità di f0]:", value=100.0) * mult
            else: target_filter = "LP"

    # --- LOGICA DELLE FORMULE IN TEMPO REALE ---
    c_idx = 0 if "R" in ctype else (1 if "L" in ctype else 2)
    op_idx = 0 if "Ampiezza e Frequenza" in op_type else (1 if "Solo Ampiezza" in op_type else 2)
    formula_text = ""

    if "Norm" in mode:
        if op_idx == 0: formula_text = "R_n = R / k" if c_idx==0 else ("L_n = (L \cdot \omega_0) / k" if c_idx==1 else "C_n = C \cdot k \cdot \omega_0")
        elif op_idx == 1: formula_text = "R_n = R / k" if c_idx==0 else ("L_n = L / k" if c_idx==1 else "C_n = C \cdot k")
        elif op_idx == 2: formula_text = "R_n = R" if c_idx==0 else ("L_n = L \cdot \omega_0" if c_idx==1 else "C_n = C \cdot \omega_0")
    else:
        if op_idx == 0: 
            if c_idx == 0: formula_text = "R = R_n \cdot k"
            elif "LP" in target_filter: formula_text = "L = (L_n \cdot k) / \omega_0" if c_idx==1 else "C = C_n / (k \cdot \omega_0)"
            elif "HP" in target_filter: formula_text = "C = 1 / (k \cdot \omega_0 \cdot L_n) \quad \text{[Inversione L} \rightarrow \text{C]}" if c_idx==1 else "L = k / (\omega_0 \cdot C_n) \quad \text{[Inversione C} \rightarrow \text{L]}"
            elif "BP" in target_filter: formula_text = "L_s = (k \cdot L_n) / B, \quad C_s = B / (k \cdot \omega_0^2 \cdot L_n)" if c_idx==1 else "C_p = C_n / (k \cdot B), \quad L_p = (k \cdot B) / (\omega_0^2 \cdot C_n)"
            elif "BS" in target_filter: formula_text = "L_p = (k \cdot B \cdot L_n) / \omega_0^2, \quad C_p = 1 / (k \cdot B \cdot L_n)" if c_idx==1 else "C_s = (B \cdot C_n) / (k \cdot \omega_0^2), \quad L_s = k / (B \cdot C_n)"
        else:
            if c_idx == 0: formula_text = "R = R_n \cdot k" if op_idx==1 else "R = R_n"
            else: formula_text = "\text{Per trasformazioni diverse dal LP->LP è richiesta la scalatura completa (Amp+Freq)}"

    st.markdown(f"<div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid {Theme.GLASS_BORDER};'><span style='color: {Theme.TEXT_SECONDARY}; font-size: 14px;'>Modello Matematico Applicato:</span><br><br> ${formula_text}$ </div><br>", unsafe_allow_html=True)

    # --- CALCOLO EFFETTIVO ---
    if st.button("Sintetizza Valore", type="primary", use_container_width=True):
        st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        try:
            if "Norm" in mode:
                res = 0.0; unit = "Ω_n" if c_idx == 0 else ("H_n" if c_idx == 1 else "F_n")
                if op_idx == 0: res = val_comp/k_val if c_idx==0 else ((w0*val_comp)/k_val if c_idx==1 else k_val*w0*val_comp)
                elif op_idx == 1: res = val_comp/k_val if c_idx==0 else (val_comp/k_val if c_idx==1 else k_val*val_comp)
                elif op_idx == 2: res = val_comp if c_idx==0 else (w0*val_comp if c_idx==1 else w0*val_comp)
                st.markdown(f"<h2 style='text-align:center; color:{Theme.SUCCESS};'>{format_eng(res, unit)}</h2>", unsafe_allow_html=True)
            else:
                if op_idx != 0 and c_idx != 0 and "LP" not in target_filter:
                    st.error("Errore: Le trasformazioni di frequenza per HP, BP e BS richiedono la scalatura combinata Ampiezza e Frequenza.")
                else:
                    if op_idx == 1:
                        res_str = format_with_e24(k_val * val_comp, 'Ω') if c_idx==0 else (format_with_e24(k_val * val_comp, 'H') if c_idx==1 else format_with_e24(val_comp / k_val, 'F'))
                    elif op_idx == 2:
                        res_str = format_with_e24(val_comp, 'Ω') if c_idx==0 else (format_with_e24(val_comp / w0, 'H') if c_idx==1 else format_with_e24(val_comp / w0, 'F'))
                    else:
                        if c_idx == 0: res_str = format_with_e24(k_val * val_comp, 'Ω')
                        elif "LP" in target_filter:
                            res_str = format_with_e24((k_val * val_comp) / w0, 'H') if c_idx==1 else format_with_e24(val_comp / (w0 * k_val), 'F')
                        elif "HP" in target_filter:
                            res_str = format_with_e24(1.0 / (k_val * w0 * val_comp), 'F') + f"<br><span style='color:{Theme.WARNING};font-size:14px;'>(Convertito da L a C)</span>" if c_idx==1 else format_with_e24(k_val / (w0 * val_comp), 'H') + f"<br><span style='color:{Theme.WARNING};font-size:14px;'>(Convertito da C a L)</span>"
                        elif "BP" in target_filter:
                            if c_idx == 1: res_str = f"<span style='color:{Theme.TEXT_SECONDARY}'>Ramo Serie LC:</span><br>L_s = {format_with_e24((k_val * val_comp) / B, 'H')}<br>C_s = {format_with_e24(B / (k_val * (w0**2) * val_comp), 'F')}"
                            elif c_idx == 2: res_str = f"<span style='color:{Theme.TEXT_SECONDARY}'>Ramo Parallelo LC:</span><br>C_p = {format_with_e24(val_comp / (k_val * B), 'F')}<br>L_p = {format_with_e24((k_val * B) / ((w0**2) * val_comp), 'H')}"
                        else: # BS
                            if c_idx == 1: res_str = f"<span style='color:{Theme.TEXT_SECONDARY}'>Ramo Parallelo LC:</span><br>L_p = {format_with_e24((k_val * B * val_comp) / (w0**2), 'H')}<br>C_p = {format_with_e24(1.0 / (k_val * B * val_comp), 'F')}"
                            elif c_idx == 2: res_str = f"<span style='color:{Theme.TEXT_SECONDARY}'>Ramo Serie LC:</span><br>C_s = {format_with_e24((B * val_comp) / (k_val * (w0**2)), 'F')}<br>L_s = {format_with_e24(k_val / (B * val_comp), 'H')}"
                    
                    st.markdown(f"<div style='text-align:center; font-size:22px; line-height: 1.5;'>{res_str}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Errore matematico nei dati inseriti: {e}")

# ==========================================
# TAB 2: SINTESI PARAMETRICA
# ==========================================
with tab_sintesi:
    c1, c2, c3 = st.columns(3)
    with c1:
        famiglia = st.selectbox("Famiglia:", ["Butterworth", "Chebyshev", "Bessel (Solo Bode)"])
        risposta = st.selectbox("Risposta:", ["Low-Pass (LP)", "High-Pass (HP)", "Band-Pass (BP)", "Band-Stop/Notch (BS)"])
        r_code = "LP" if "LP" in risposta else ("HP" if "HP" in risposta else ("BP" if "BP" in risposta else "BS"))
    with c2:
        spec_type_ui = st.selectbox("Ottimizzazione:", ["Banda Oscura (Match Ap)", "Banda Passante (Match As)"])
        first_elem = st.selectbox("Cella IN:", ["Induttore Serie (L)", "Condensatore Shunt (C)"])
    with c3:
        R_load = st.number_input("R_load (Ω):", value=50.0)
        col_a1, col_a2 = st.columns(2)
        with col_a1: ap = st.number_input("αp (dB):", value=1.0)
        with col_a2: As = st.number_input("αs (dB):", value=40.0)

    cf1, cf2 = st.columns([1, 1.5])
    with cf1:
        if r_code in ["BP", "BS"]:
            f_center = st.number_input("Freq. Centrale f0 (Hz):", value=1000.0)
            fp = st.number_input("Banda Passante Bp (Hz):", value=100.0)
            fs = st.number_input("Banda Oscura Bs (Hz):", value=500.0)
        else:
            f_center = 1000.0
            fp = st.number_input("f_pass (Hz):", value=1000.0)
            fs = st.number_input("f_stop (Hz):", value=5000.0)
    with cf2:
        fig_m, ax_m = plt.subplots(figsize=(3.5, 2.5)); fig_m.patch.set_facecolor('none')
        draw_tolerance_mask(ax_m, r_code, f_center, fp, fs, ap, As)
        fig_m.tight_layout()
        st.pyplot(fig_m, use_container_width=False)

    st.button("Genera Schematico e Cauer", type="primary", use_container_width=True)
    
    first_char = "L" if "Induttore" in first_elem else "C"
    filtro = FilterSynthesizer(famiglia, r_code, "stop" if "Oscura" in spec_type_ui else "pass", fp, fs, ap, As, R_load, first_char, f_center)
    res = filtro.synthesize()
    st.session_state['filtro'] = filtro 
    
    c_log, c_circ = st.columns([1, 2.5])
    with c_log:
        log = f"<div style='background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; font-family: {Theme.FONT_CODE};'>"
        log += f"<span style='color:{Theme.SUCCESS};'>=== SINTESI {r_code} ===<br>N = {res['N']}<br>"
        if r_code in ["LP", "HP"]: log += f"f0 = {res['f0']:.1f} Hz<br></span>"
        else: log += f"B0 = {res['B0']:.1f} Hz<br></span>"
        
        log += f"<hr style='border-color: {Theme.GLASS_BORDER};'><span style='color:{Theme.ACCENT};'>BOM (Distinta):</span><br>"
        if non_vuoto := res['network']:
            for c in non_vuoto:
                if 'val_L' in c: log += f"<b>{c['type']}</b>:<br>L: {format_with_e24(c['val_L'],'H', html=False)}<br>C: {format_with_e24(c['val_C'],'F', html=False)}<br><br>"
                else: log += f"<b>{c['type']}</b>:<br>{format_with_e24(c['val'], 'H' if 'L' in c['type'] else 'F', html=False)}<br><br>"
        else:
            log += f"<br><span style='color:{Theme.WARNING}'>Non supportata per {famiglia}</span>"
        log += "</div>"
        st.markdown(log, unsafe_allow_html=True)
        
    with c_circ:
        fig_c, ax_c = plt.subplots(figsize=(6, 3)); fig_c.patch.set_facecolor('none')
        draw_circuit(ax_c, res['network'], R_load)
        fig_c.tight_layout()
        st.pyplot(fig_c)

# ==========================================
# TAB 3: ANALISI BODE
# ==========================================
with tab_bode:
    cb1, cb2 = st.columns(2)
    with cb1: bode_type = st.selectbox("Metrica d'Ampiezza:", ["|H(jω)| e Fase (Lineare)", "10·log|H(jω)| e Fase (Potenza)", "Guadagno: 20·log|H(jω)| e Fase", "Attenuazione: -20·log|H(jω)| e Fase"])
    with cb2: bode_scale = st.selectbox("Scala Assi:", ["Semilogaritmica (X-Log, Y-Lin)", "Bilogaritmica (X-Log, Y-Log)", "Lineare"])
        
    if 'filtro' in st.session_state:
        fig_b, (ax_mag, ax_pha) = plt.subplots(2, 1, figsize=(10, 6)); fig_b.patch.set_facecolor('none')
        draw_bode(ax_mag, ax_pha, st.session_state['filtro'], bode_type, bode_scale)
        fig_b.tight_layout(pad=2.0)
        st.pyplot(fig_b)