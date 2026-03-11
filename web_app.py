import streamlit as st
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

from core.filter_logic import FilterSynthesizer
from core.theme import Theme
from core.whitelist import WHITELIST_EMAILS, PASSWORD_CORRETTA

st.set_page_config(page_title="FiltroTool Pro", page_icon="⚡", layout="wide")
st.markdown(Theme.get_streamlit_css(), unsafe_allow_html=True)

# --- UTILITIES MATEMATICHE ---
def format_eng(value, base_unit):
    if value == 0: return f"0.000 {base_unit}"
    degree = int(math.floor(math.log10(abs(value)) / 3))
    prefixes = { -4: 'p', -3: 'n', -2: 'µ', -1: 'm', 0: '', 1: 'k', 2: 'M', 3: 'G' }
    degree = max(min(degree, 3), -4)
    scaled_val = value * (1000 ** -degree)
    return f"{scaled_val:.3f} {prefixes[degree]}{base_unit}"

def get_nearest_E24(value):
    if value == 0: return 0
    E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
    power = math.floor(math.log10(value))
    base = value / (10**power)
    closest_base = min(E24, key=lambda x: abs(x - base))
    return closest_base * (10**power)

def format_with_e24(val, base_unit):
    return f"<span style='color:{Theme.TEXT_PRIMARY}; font-weight:bold;'>{format_eng(val, base_unit)}</span> <br><span style='color:{Theme.TEXT_SECONDARY}; font-size:12px;'>(E24: ~{format_eng(get_nearest_E24(val), base_unit)})</span>"

# --- GRAFICA DIDATTICA (MASCHERA DI TOLLERANZA) ---
def draw_tolerance_mask(resp_type, f_center, fp, fs, ap, As):
    # Dimensioni compatte identiche alla versione Desktop
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    
    color_pass = (50/255, 215/255, 75/255, 0.2) # Verde Apple
    color_stop = (255/255, 55/255, 95/255, 0.2) # Rosso Apple
    txt_col = '#FFFFFF'
    
    ax.invert_yaxis() # L'attenuazione cresce verso il basso
    max_a = max(As * 1.2, 60)
    
    def mark_point(x, y, label, ha='left', va='bottom', offset_x=1.1, offset_y=-2):
        ax.plot(x, y, 'o', color='white', markersize=4)
        ax.text(x * offset_x, y + offset_y, label, color=txt_col, ha=ha, va=va, fontsize=8, fontweight='bold')

    if resp_type == "LP":
        ax.fill_between([1e-5, fp], 0, ap, color=color_pass, lw=0)
        ax.fill_between([fs, 1e7], As, max_a, color=color_stop, lw=0)
        ax.plot([1e-5, fp, fs, 1e7], [0, ap, As, As], color='gray', lw=1.5, ls='--')
        
        mark_point(fp, ap, "fp, αp", ha='right', offset_x=0.9)
        mark_point(fs, As, "fs, αs", ha='left', offset_x=1.1, offset_y=3)
        ax.set_xlim(max(1, fp/10), fs*10)

    elif resp_type == "HP":
        ax.fill_between([1e-5, fs], As, max_a, color=color_stop, lw=0)
        ax.fill_between([fp, 1e7], 0, ap, color=color_pass, lw=0)
        ax.plot([1e-5, fs, fp, 1e7], [As, As, ap, 0], color='gray', lw=1.5, ls='--')
        
        mark_point(fs, As, "fs, αs", ha='right', offset_x=0.9, offset_y=3)
        mark_point(fp, ap, "fp, αp", ha='left', offset_x=1.1)
        ax.set_xlim(max(1, fs/10), fp*10)

    elif resp_type in ["BP", "BS"]:
        Bp, Bs = fp, fs
        f0 = f_center
        
        fp1 = (-Bp + math.sqrt(Bp**2 + 4*f0**2))/2; fp2 = fp1 + Bp
        fs1 = (-Bs + math.sqrt(Bs**2 + 4*f0**2))/2; fs2 = fs1 + Bs
        
        if resp_type == "BP":
            ax.fill_between([1e-5, fs1], As, max_a, color=color_stop, lw=0)
            ax.fill_between([fp1, fp2], 0, ap, color=color_pass, lw=0)
            ax.fill_between([fs2, 1e7], As, max_a, color=color_stop, lw=0)
            ax.plot([1e-5, fs1, fp1, fp2, fs2, 1e7], [As, As, ap, ap, As, As], color='gray', lw=1.5, ls='--')
            
            mark_point(fp1, ap, "fp1", ha='right', offset_x=0.9)
            mark_point(fp2, ap, "fp2", ha='left', offset_x=1.1)
            
            ax.annotate('', xy=(fp1, ap/2), xytext=(fp2, ap/2), arrowprops=dict(arrowstyle='<->', color='white'))
            ax.text(f0, ap/2 - 2, "B_pass", color='white', ha='center', fontsize=8)
            ax.set_xlim(fs1/2, fs2*2)
            
        else: # BS (Notch)
            ax.fill_between([1e-5, fp1], 0, ap, color=color_pass, lw=0)
            ax.fill_between([fs1, fs2], As, max_a, color=color_stop, lw=0)
            ax.fill_between([fp2, 1e7], 0, ap, color=color_pass, lw=0)
            ax.plot([1e-5, fp1, fs1, fs2, fp2, 1e7], [0, ap, As, As, ap, 0], color='gray', lw=1.5, ls='--')
            
            mark_point(fs1, As, "fs1", ha='right', offset_x=0.9, offset_y=3)
            mark_point(fs2, As, "fs2", ha='left', offset_x=1.1, offset_y=3)
            
            ax.annotate('', xy=(fs1, As-5), xytext=(fs2, As-5), arrowprops=dict(arrowstyle='<->', color='white'))
            ax.text(f0, As-8, "B_stop", color='white', ha='center', fontsize=8)
            ax.set_xlim(fp1/2, fp2*2)
            
    ax.set_xscale('log')
    ax.set_ylim(max_a, -2)
    ax.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
    for spine in ax.spines.values(): spine.set_color('none')
    ax.grid(True, which="both", ls="-", color="white", alpha=0.05)
    return fig

# --- MOTORE CAD CIRCUITO PER WEB ---
def draw_circuit_st(network, R_load):
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    ax.axis('off')
    x, y_top, y_bot = 0, 1, 0
    
    ax.plot([x, x+0.2], [y_top, y_top], color='white', lw=2)
    ax.plot([x, x+0.2], [y_bot, y_bot], color='white', lw=2)
    ax.text(x-0.1, 0.5, "IN", color='white', ha='right', va='center', fontweight='bold', fontsize=12)
    x += 0.2
    
    for comp in network:
        ctype = comp['type']
        val_eng = format_eng(comp.get('val', 0), 'H' if 'L' in ctype else 'F')
        
        def draw_L(xi, yi, rot='h', col=Theme.WARNING):
            t = np.linspace(0, 4*np.pi, 100)
            if rot == 'h': ax.plot(np.linspace(xi, xi+0.4, 100), yi + 0.12*np.abs(np.sin(t)), color=col, lw=2.5)
            else: ax.plot(xi + 0.12*np.abs(np.sin(t)), np.linspace(yi, yi-0.4, 100), color=col, lw=2.5)
            
        def draw_C(xi, yi, rot='h', col=Theme.ACCENT):
            if rot == 'h':
                ax.plot([xi, xi+0.15], [yi, yi], color='white', lw=2); ax.plot([xi+0.25, xi+0.4], [yi, yi], color='white', lw=2)
                ax.plot([xi+0.15, xi+0.15], [yi-0.2, yi+0.2], color=col, lw=2.5); ax.plot([xi+0.25, xi+0.25], [yi-0.2, yi+0.2], color=col, lw=2.5)
            else:
                ax.plot([xi, xi], [yi, yi-0.15], color='white', lw=2); ax.plot([xi, xi], [yi-0.25, yi-0.4], color='white', lw=2)
                ax.plot([xi-0.2, xi+0.2], [yi-0.15, yi-0.15], color=col, lw=2.5); ax.plot([xi-0.2, xi+0.2], [yi-0.25, yi-0.25], color=col, lw=2.5)

        if ctype in ["L_series", "C_series"]: 
            ax.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2); ax.plot([x, x+0.2], [y_top, y_top], color='white', lw=2); ax.plot([x+0.6, x+0.8], [y_top, y_top], color='white', lw=2)
            if 'L' in ctype: draw_L(x+0.2, y_top, 'h', Theme.WARNING)
            else: draw_C(x+0.2, y_top, 'h', Theme.ACCENT)
            ax.text(x+0.4, y_top+0.3, val_eng, color='white', ha='center', fontsize=9)
            x += 0.8
        elif ctype in ["L_shunt", "C_shunt"]:
            ax.plot([x, x+0.8], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
            ax.plot([x+0.4, x+0.4], [y_top, y_top-0.3], color='white', lw=2); ax.plot([x+0.4, x+0.4], [y_bot+0.3, y_bot], color='white', lw=2)
            if 'L' in ctype: draw_L(x+0.4, y_top-0.3, 'v', Theme.WARNING)
            else: draw_C(x+0.4, y_top-0.3, 'v', Theme.ACCENT)
            ax.text(x+0.6, 0.5, val_eng, color='white', va='center', fontsize=9)
            x += 0.8
        elif ctype == "LC_series_series": 
            ax.plot([x, x+1.2], [y_bot, y_bot], color='white', lw=2); ax.plot([x, x+0.1], [y_top, y_top], color='white', lw=2)
            draw_L(x+0.1, y_top, 'h', Theme.WARNING); ax.plot([x+0.5, x+0.7], [y_top, y_top], color='white', lw=2)
            draw_C(x+0.7, y_top, 'h', Theme.ACCENT); ax.plot([x+1.1, x+1.2], [y_top, y_top], color='white', lw=2)
            x += 1.2
        elif ctype == "LC_shunt_parallel":
            ax.plot([x, x+1.0], [y_top, y_top], color='white', lw=2); ax.plot([x, x+1.0], [y_bot, y_bot], color='white', lw=2)
            ax.plot([x+0.5, x+0.5], [y_top, y_top-0.1], color='white', lw=2); ax.plot([x+0.5, x+0.5], [y_bot+0.1, y_bot], color='white', lw=2)
            ax.plot([x+0.2, x+0.8], [y_top-0.1, y_top-0.1], color='white', lw=2); ax.plot([x+0.2, x+0.8], [y_bot+0.1, y_bot+0.1], color='white', lw=2)
            ax.plot([x+0.2, x+0.2], [y_top-0.1, y_top-0.3], color='white', lw=2); ax.plot([x+0.2, x+0.2], [y_bot+0.3, y_bot+0.1], color='white', lw=2)
            ax.plot([x+0.8, x+0.8], [y_top-0.1, y_top-0.3], color='white', lw=2); ax.plot([x+0.8, x+0.8], [y_bot+0.3, y_bot+0.1], color='white', lw=2)
            draw_C(x+0.2, y_top-0.3, 'v', Theme.ACCENT); draw_L(x+0.8, y_top-0.3, 'v', Theme.WARNING)
            x += 1.0
        elif ctype == "LC_series_parallel": 
            ax.plot([x, x+1.2], [y_bot, y_bot], color='white', lw=2); ax.plot([x, x+0.2], [y_top, y_top], color='white', lw=2); ax.plot([x+1.0, x+1.2], [y_top, y_top], color='white', lw=2)
            ax.plot([x+0.2, x+0.2], [y_top-0.3, y_top+0.3], color='white', lw=2); ax.plot([x+1.0, x+1.0], [y_top-0.3, y_top+0.3], color='white', lw=2)
            ax.plot([x+0.2, x+0.4], [y_top+0.3, y_top+0.3], color='white', lw=2); ax.plot([x+0.8, x+1.0], [y_top+0.3, y_top+0.3], color='white', lw=2)
            ax.plot([x+0.2, x+0.4], [y_top-0.3, y_top-0.3], color='white', lw=2); ax.plot([x+0.8, x+1.0], [y_top-0.3, y_top-0.3], color='white', lw=2)
            draw_L(x+0.4, y_top+0.3, 'h', Theme.WARNING); draw_C(x+0.4, y_top-0.3, 'h', Theme.ACCENT)
            x += 1.2
        elif ctype == "LC_shunt_series":
            ax.plot([x, x+0.8], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
            ax.plot([x+0.4, x+0.4], [y_top, y_top-0.1], color='white', lw=2); draw_C(x+0.4, y_top-0.1, 'v', Theme.ACCENT)
            ax.plot([x+0.4, x+0.4], [y_top-0.5, y_top-0.6], color='white', lw=2); draw_L(x+0.4, y_top-0.6, 'v', Theme.WARNING)
            ax.plot([x+0.4, x+0.4], [y_bot+0.1, y_bot], color='white', lw=2)
            x += 0.8
            
    ax.plot([x, x+0.4], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.4], [y_bot, y_bot], color='white', lw=2)
    ax.plot([x+0.4, x+0.4], [y_top, y_top-0.3], color='white', lw=2); ax.plot([x+0.4, x+0.4], [y_bot+0.3, y_bot], color='white', lw=2)
    y_zig = np.linspace(y_top-0.3, y_bot+0.3, 7); x_zig = x+0.4 + np.array([0, 0.15, -0.15, 0.15, -0.15, 0.15, 0])
    ax.plot(x_zig, y_zig, color=Theme.SUCCESS, lw=2.5)
    ax.text(x+0.65, 0.5, f"RL\n{R_load}Ω", color=Theme.SUCCESS, va='center', fontweight='bold', fontsize=10)
    ax.plot([x+0.4, x+0.6], [y_top, y_top], color='white', lw=2); ax.plot([x+0.4, x+0.6], [y_bot, y_bot], color='white', lw=2)
    ax.text(x+0.75, 0.5, "OUT", color='white', ha='left', va='center', fontweight='bold', fontsize=12)
    ax.set_xlim(-0.5, x+1.2); ax.set_ylim(-0.8, 1.8)
    return fig

# --- AUTENTICAZIONE ---
if 'autenticato' not in st.session_state: st.session_state['autenticato'] = False
if not st.session_state['autenticato']:
    st.markdown(f"<h1 style='text-align: center;'>🔒 FiltroTool Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email Unige:")
            password = st.text_input("Password:", type="password")
            if st.form_submit_button("Accedi", type="primary"):
                if email in WHITELIST_EMAILS and password == PASSWORD_CORRETTA:
                    st.session_state['autenticato'] = True; st.rerun()
                else: st.error("Accesso negato. Utente non autorizzato o password errata.")
    st.stop()

# --- HEADER MAIN ---
st.markdown(f"<h1 style='text-align: center;'>FiltroTool Pro</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {Theme.ACCENT}; font-weight: bold;'>Sintesi Avanzata Circuiti Passivi</p>", unsafe_allow_html=True)

tab_norm, tab_sintesi, tab_bode = st.tabs(["⚖️ De/Normalizzazione", "🎛️ Sintesi Parametrica", "📈 Analisi Bode"])

# --- TAB DE/NORMALIZZAZIONE ---
with tab_norm:
    mode = st.radio("Seleziona Operazione:", ["Normalizzazione Fisica", "Denormalizzazione Fisica"], horizontal=True)
    
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Parametri di Riferimento**")
            val_comp = st.number_input("Valore Componente:", value=1.0, format="%.6g")
            k_val = st.number_input("Fattore k (Resistenza Carico):", value=1000.0)
            cc1, cc2 = st.columns([2,1])
            with cc1: val_freq = st.number_input("Frequenza (f0 / ω0):", value=1000.0)
            with cc2: unit_freq = st.selectbox("Unità:", ["Hz", "kHz", "MHz", "rad/s"])
            mult = 2 * math.pi if "Hz" in unit_freq else 1.0
            if unit_freq == "kHz": mult *= 1e3; 
            if unit_freq == "MHz": mult *= 1e6
            w0 = val_freq * mult

        with c2:
            st.markdown(f"**Impostazioni e Target**")
            op_type = st.selectbox("Trasformazione:", ["Ampiezza e Frequenza", "Solo Ampiezza", "Solo Frequenza"])
            ctype = st.selectbox("Componente Originale:", ["Resistore (R)", "Induttore (L)", "Condensatore (C)"])
            
            B = 1.0
            if "Denorm" in mode:
                target_filter = st.selectbox("Architettura Target:", ["Passa-Basso (LP)", "Passa-Alto (HP)", "Passa-Banda (BP)", "Elimina-Banda (BS)"])
                if "BP" in target_filter or "BS" in target_filter:
                    val_bw = st.number_input("Banda (B) [stessa unità]:", value=100.0)
                    B = val_bw * mult
            else: target_filter = "LP"

    if st.button("Sintetizza Valore", type="primary", use_container_width=True):
        c_idx = 0 if "R" in ctype else (1 if "L" in ctype else 2)
        op_idx = 0 if "Ampiezza e Frequenza" in op_type else (1 if "Solo Ampiezza" in op_type else 2)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        if "Norm" in mode:
            res = 0.0
            unit = "Ω_n" if c_idx == 0 else ("H_n" if c_idx == 1 else "F_n")
            if op_idx == 0:
                if c_idx == 0: res = val_comp / k_val
                elif c_idx == 1: res = (w0 * val_comp) / k_val
                elif c_idx == 2: res = k_val * w0 * val_comp
            st.markdown(f"<h3 style='text-align:center; color:{Theme.SUCCESS};'>{format_eng(res, unit)}</h3>", unsafe_allow_html=True)
        else:
            if "LP" in target_filter:
                if c_idx == 0: res_str = format_with_e24(k_val * val_comp, 'Ω')
                elif c_idx == 1: res_str = format_with_e24((k_val * val_comp) / w0, 'H')
                elif c_idx == 2: res_str = format_with_e24(val_comp / (w0 * k_val), 'F')
                st.markdown(f"<div style='text-align:center; font-size:24px;'>{res_str}</div>", unsafe_allow_html=True)

# --- TAB SINTESI PARAMETRICA ---
with tab_sintesi:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Architettura**")
        famiglia = st.selectbox("Famiglia:", ["Butterworth", "Chebyshev"])
        risposta = st.selectbox("Risposta:", ["Low-Pass (LP)", "High-Pass (HP)", "Band-Pass (BP)", "Band-Stop/Notch (BS)"])
        r_code = "LP" if "LP" in risposta else ("HP" if "HP" in risposta else ("BP" if "BP" in risposta else "BS"))
    with c2:
        st.markdown("**Topologia**")
        spec_type_ui = st.selectbox("Ottimizzazione:", ["Banda Oscura (Match Ap)", "Banda Passante (Match As)"])
        first_elem = st.selectbox("Cella IN:", ["Induttore Serie (L)", "Condensatore Shunt (C)"])
    with c3:
        st.markdown("**Specifiche Base**")
        R_load = st.number_input("R_load (Ω):", value=50.0)
        col_a1, col_a2 = st.columns(2)
        with col_a1: ap = st.number_input("αp (dB):", value=1.0)
        with col_a2: As = st.number_input("αs (dB):", value=40.0)

    # Input specifici e Maschera Didattica
    cf1, cf2 = st.columns([1, 1.5])
    with cf1:
        st.markdown("**Frequenze Operative**")
        if r_code in ["BP", "BS"]:
            f_center = st.number_input("Freq. Centrale f0 (Hz):", value=1000.0)
            fp = st.number_input("Banda Passante Bp (Hz):", value=100.0)
            fs = st.number_input("Banda Oscura Bs (Hz):", value=500.0)
        else:
            f_center = 1000.0
            fp = st.number_input("f_pass (Hz):", value=1000.0)
            fs = st.number_input("f_stop (Hz):", value=5000.0)
    with cf2:
        st.markdown("**Maschera di Tolleranza**")
        # Passiamo use_container_width=False in modo che matplotlib mantenga le dimensioni esatte (3.5, 2.5) richieste!
        st.pyplot(draw_tolerance_mask(r_code, f_center, fp, fs, ap, As), use_container_width=False)

    btn_calc = st.button("Genera Schematico e Cauer", type="primary", use_container_width=True)
    
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
        log += f"<hr style='border-color: {Theme.GLASS_BORDER};'><span style='color:{Theme.ACCENT};'>BOM:</span><br>"
        for c in res['network']:
            if 'val_L' in c: log += f"<b>{c['type']}</b>:<br>L:{format_eng(c['val_L'],'H')}<br>C:{format_eng(c['val_C'],'F')}<br>"
            else: log += f"<b>{c['type']}</b>: {format_eng(c['val'], 'H' if 'L' in c['type'] else 'F')}<br>"
        log += "</div>"
        st.markdown(log, unsafe_allow_html=True)
    with c_circ:
        st.pyplot(draw_circuit_st(res['network'], R_load))

# --- TAB ANALISI BODE ---
with tab_bode:
    cb1, cb2 = st.columns(2)
    with cb1:
        bode_type = st.selectbox("Metrica d'Ampiezza:", ["|H(jω)| e Fase (Lineare)", "10·log|H(jω)| e Fase (Potenza)", "Guadagno: 20·log|H(jω)| e Fase", "Attenuazione: -20·log|H(jω)| e Fase"])
    with cb2:
        bode_scale = st.selectbox("Scala Assi:", ["Semilogaritmica (X-Log, Y-Lin)", "Bilogaritmica (X-Log, Y-Log)", "Lineare"])
        
    if 'filtro' in st.session_state:
        f_obj = st.session_state['filtro']
        b, a = f_obj.get_transfer_function()
        f_ref = res['f0'] if r_code in ["LP", "HP"] else f_center
        w, h = signal.freqs(b, a, worN=np.logspace(math.log10(max(1, f_ref/100)), math.log10(f_ref*100), 1000))
        f_asse = w / (2 * np.pi)
        
        mag_linear = abs(h)
        mag_linear[mag_linear == 0] = np.finfo(float).eps
        phase_rad = np.unwrap(np.angle(h))
        
        plt.style.use('dark_background')
        fig_b, (ax_mag, ax_pha) = plt.subplots(2, 1, figsize=(10, 6))
        fig_b.patch.set_facecolor('none')
        ax_mag.set_facecolor('none')
        ax_pha.set_facecolor('none')
        
        if "Lineare" in bode_type: y_mag, y_label, m_col = mag_linear, "|H|", Theme.SUCCESS
        elif "10·log" in bode_type: y_mag, y_label, m_col = 10 * np.log10(mag_linear), "10·log|H|", Theme.ACCENT
        elif "Guadagno" in bode_type: y_mag, y_label, m_col = 20 * np.log10(mag_linear), "Guadagno [dB]", Theme.ACCENT
        else: y_mag, y_label, m_col = -20 * np.log10(mag_linear), "Attenuazione [dB]", Theme.WARNING
        
        ax_mag.plot(f_asse, y_mag, color=m_col, lw=2.5) 
        ax_mag.set_ylabel(y_label, color=Theme.TEXT_SECONDARY, fontweight='bold')
        ax_mag.set_title(f"Diagramma di Bode - {f_obj.filter_type} {f_obj.response_type}", color="white", fontweight='bold')
        ax_pha.plot(f_asse, phase_rad, color=Theme.DANGER, lw=2.5)
        ax_pha.set_ylabel("Fase [rad]", color=Theme.TEXT_SECONDARY, fontweight='bold')
        
        for ax in [ax_mag, ax_pha]:
            if "Lineare" not in bode_scale: ax.set_xscale('log')
            if "Bilogaritmica" in bode_scale and "Lineare" not in bode_type: ax.set_yscale('symlog')
            ax.grid(True, alpha=0.1)
            ax.tick_params(colors=Theme.TEXT_SECONDARY)
            for spine in ax.spines.values(): spine.set_color('none')
            
        fig_b.tight_layout(pad=2.0)
        st.pyplot(fig_b)