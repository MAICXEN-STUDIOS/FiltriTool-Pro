# core/shared_graphics.py

import math
import numpy as np
import scipy.signal as signal
import matplotlib.patches as patches
from core.theme import Theme

# --- FORMATTAZIONE E E24 ---
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

def format_with_e24(val, base_unit, html=True):
    eng = format_eng(val, base_unit)
    e24 = format_eng(get_nearest_E24(val), base_unit)
    if html: return f"<span style='color:{Theme.TEXT_PRIMARY}; font-weight:bold;'>{eng}</span> <br><span style='color:{Theme.TEXT_SECONDARY}; font-size:12px;'>(E24: ~{e24})</span>"
    return f"{eng}   (E24: ~{e24})"

# --- MASCHERA DIDATTICA ---
def draw_tolerance_mask(ax, resp_type, f_center, fp, fs, ap, As):
    ax.clear()
    ax.invert_yaxis()
    max_a = max(As * 1.2, 60)
    
    color_pass = (50/255, 215/255, 75/255, 0.2)
    color_stop = (255/255, 55/255, 95/255, 0.2)
    
    def mark_point(x, y, label, ha='left', va='bottom', ox=1.1, oy=-2):
        ax.plot(x, y, 'o', color='white', markersize=4)
        ax.text(x * ox, y + oy, label, color='#FFFFFF', ha=ha, va=va, fontsize=8, fontweight='bold')

    if resp_type == "LP":
        ax.fill_between([1e-5, fp], 0, ap, color=color_pass, lw=0)
        ax.fill_between([fs, 1e7], As, max_a, color=color_stop, lw=0)
        ax.plot([1e-5, fp, fs, 1e7], [0, ap, As, As], color='gray', lw=1.5, ls='--')
        mark_point(fp, ap, "fp", ha='right', ox=0.9)
        mark_point(fs, As, "fs", ha='left', ox=1.1, oy=3)
        ax.set_xlim(max(1, fp/10), fs*10)

    elif resp_type == "HP":
        ax.fill_between([1e-5, fs], As, max_a, color=color_stop, lw=0)
        ax.fill_between([fp, 1e7], 0, ap, color=color_pass, lw=0)
        ax.plot([1e-5, fs, fp, 1e7], [As, As, ap, 0], color='gray', lw=1.5, ls='--')
        mark_point(fs, As, "fs", ha='right', ox=0.9, oy=3)
        mark_point(fp, ap, "fp", ha='left', ox=1.1)
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
            mark_point(fp1, ap, "fp1", ha='right', ox=0.9); mark_point(fp2, ap, "fp2", ha='left', ox=1.1)
            ax.annotate('', xy=(fp1, ap/2), xytext=(fp2, ap/2), arrowprops=dict(arrowstyle='<->', color='white'))
            ax.text(f0, ap/2 - 2, "B_pass", color='white', ha='center', fontsize=8)
            ax.set_xlim(fs1/2, fs2*2)
        else:
            ax.fill_between([1e-5, fp1], 0, ap, color=color_pass, lw=0)
            ax.fill_between([fs1, fs2], As, max_a, color=color_stop, lw=0)
            ax.fill_between([fp2, 1e7], 0, ap, color=color_pass, lw=0)
            ax.plot([1e-5, fp1, fs1, fs2, fp2, 1e7], [0, ap, As, As, ap, 0], color='gray', lw=1.5, ls='--')
            mark_point(fs1, As, "fs1", ha='right', ox=0.9, oy=3); mark_point(fs2, As, "fs2", ha='left', ox=1.1, oy=3)
            ax.annotate('', xy=(fs1, As-5), xytext=(fs2, As-5), arrowprops=dict(arrowstyle='<->', color='white'))
            ax.text(f0, As-8, "B_stop", color='white', ha='center', fontsize=8)
            ax.set_xlim(fp1/2, fp2*2)
            
    ax.set_xscale('log')
    ax.set_ylim(max_a, -2)
    ax.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
    for spine in ax.spines.values(): spine.set_color('none')
    ax.grid(True, which="both", ls="-", color="white", alpha=0.05)

# --- DISEGNO CIRCUITO ---
def draw_circuit(ax, network, R_load):
    ax.clear()
    ax.axis('off')
    if not network:
        ax.text(0.5, 0.5, "Rete non disponibile per l'approssimazione selezionata.\nFiltro calcolato solo per diagramma di Bode.", color=Theme.WARNING, ha='center', va='center')
        return

    x, y_top, y_bot = 0, 1, 0
    ax.plot([x, x+0.2], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.2], [y_bot, y_bot], color='white', lw=2)
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
            if 'L' in ctype: draw_L(x+0.2, y_top, 'h')
            else: draw_C(x+0.2, y_top, 'h')
            ax.text(x+0.4, y_top+0.3, val_eng, color='white', ha='center', fontsize=9); x += 0.8
        elif ctype in ["L_shunt", "C_shunt"]:
            ax.plot([x, x+0.8], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
            ax.plot([x+0.4, x+0.4], [y_top, y_top-0.3], color='white', lw=2); ax.plot([x+0.4, x+0.4], [y_bot+0.3, y_bot], color='white', lw=2)
            if 'L' in ctype: draw_L(x+0.4, y_top-0.3, 'v')
            else: draw_C(x+0.4, y_top-0.3, 'v')
            ax.text(x+0.6, 0.5, val_eng, color='white', va='center', fontsize=9); x += 0.8
        elif ctype == "LC_series_series": 
            ax.plot([x, x+1.2], [y_bot, y_bot], color='white', lw=2); ax.plot([x, x+0.1], [y_top, y_top], color='white', lw=2)
            draw_L(x+0.1, y_top, 'h'); ax.plot([x+0.5, x+0.7], [y_top, y_top], color='white', lw=2)
            draw_C(x+0.7, y_top, 'h'); ax.plot([x+1.1, x+1.2], [y_top, y_top], color='white', lw=2)
            x += 1.2
        elif ctype == "LC_shunt_parallel":
            ax.plot([x, x+1.0], [y_top, y_top], color='white', lw=2); ax.plot([x, x+1.0], [y_bot, y_bot], color='white', lw=2)
            ax.plot([x+0.5, x+0.5], [y_top, y_top-0.1], color='white', lw=2); ax.plot([x+0.5, x+0.5], [y_bot+0.1, y_bot], color='white', lw=2)
            ax.plot([x+0.2, x+0.8], [y_top-0.1, y_top-0.1], color='white', lw=2); ax.plot([x+0.2, x+0.8], [y_bot+0.1, y_bot+0.1], color='white', lw=2)
            ax.plot([x+0.2, x+0.2], [y_top-0.1, y_top-0.3], color='white', lw=2); ax.plot([x+0.2, x+0.2], [y_bot+0.3, y_bot+0.1], color='white', lw=2)
            ax.plot([x+0.8, x+0.8], [y_top-0.1, y_top-0.3], color='white', lw=2); ax.plot([x+0.8, x+0.8], [y_bot+0.3, y_bot+0.1], color='white', lw=2)
            draw_C(x+0.2, y_top-0.3, 'v'); draw_L(x+0.8, y_top-0.3, 'v')
            x += 1.0
        elif ctype == "LC_series_parallel": 
            ax.plot([x, x+1.2], [y_bot, y_bot], color='white', lw=2); ax.plot([x, x+0.2], [y_top, y_top], color='white', lw=2); ax.plot([x+1.0, x+1.2], [y_top, y_top], color='white', lw=2)
            ax.plot([x+0.2, x+0.2], [y_top-0.3, y_top+0.3], color='white', lw=2); ax.plot([x+1.0, x+1.0], [y_top-0.3, y_top+0.3], color='white', lw=2)
            ax.plot([x+0.2, x+0.4], [y_top+0.3, y_top+0.3], color='white', lw=2); ax.plot([x+0.8, x+1.0], [y_top+0.3, y_top+0.3], color='white', lw=2)
            ax.plot([x+0.2, x+0.4], [y_top-0.3, y_top-0.3], color='white', lw=2); ax.plot([x+0.8, x+1.0], [y_top-0.3, y_top-0.3], color='white', lw=2)
            draw_L(x+0.4, y_top+0.3, 'h'); draw_C(x+0.4, y_top-0.3, 'h')
            x += 1.2
        elif ctype == "LC_shunt_series":
            ax.plot([x, x+0.8], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.8], [y_bot, y_bot], color='white', lw=2)
            ax.plot([x+0.4, x+0.4], [y_top, y_top-0.1], color='white', lw=2); draw_C(x+0.4, y_top-0.1, 'v')
            ax.plot([x+0.4, x+0.4], [y_top-0.5, y_top-0.6], color='white', lw=2); draw_L(x+0.4, y_top-0.6, 'v')
            ax.plot([x+0.4, x+0.4], [y_bot+0.1, y_bot], color='white', lw=2)
            x += 0.8
            
    ax.plot([x, x+0.4], [y_top, y_top], color='white', lw=2); ax.plot([x, x+0.4], [y_bot, y_bot], color='white', lw=2)
    ax.plot([x+0.4, x+0.4], [y_top, y_top-0.3], color='white', lw=2); ax.plot([x+0.4, x+0.4], [y_bot+0.3, y_bot], color='white', lw=2)
    y_zig = np.linspace(y_top-0.3, y_bot+0.3, 7); x_zig = x+0.4 + np.array([0, 0.15, -0.15, 0.15, -0.15, 0.15, 0])
    ax.plot(x_zig, y_zig, color=Theme.SUCCESS, lw=2.5)
    ax.text(x+0.65, 0.5, f"RL\n{R_load}Ω", color=Theme.SUCCESS, va='center', fontweight='bold', fontsize=10)
    ax.plot([x+0.4, x+0.6], [y_top, y_top], color='white', lw=2); ax.plot([x+0.4, x+0.6], [y_bot, y_bot], color='white', lw=2)
    ax.text(x+0.75, 0.5, "OUT", color='white', ha='left', va='center', fontweight='bold', fontsize=12)
    ax.set_xlim(-0.5, x+1.2); ax.set_ylim(-1.0, 2.0)

# --- DISEGNO BODE ---
def draw_bode(ax_mag, ax_pha, filter_obj, bode_type, bode_scale):
    ax_mag.clear()
    ax_pha.clear()
    
    b, a = filter_obj.get_transfer_function()
    f_ref = filter_obj.f0 if filter_obj.response_type in ["LP", "HP"] else filter_obj.f_center
    if f_ref <= 0: f_ref = 1000 
    
    w, h = signal.freqs(b, a, worN=np.logspace(math.log10(max(1, f_ref/100)), math.log10(f_ref*100), 1000))
    f_asse = w / (2 * np.pi)
    
    mag_linear = abs(h)
    mag_linear[mag_linear == 0] = np.finfo(float).eps 
    phase_rad = np.unwrap(np.angle(h))
    
    if "Lineare" in bode_type: y_mag, y_label, mag_color = mag_linear, '|H(jω)|', Theme.SUCCESS
    elif "10·log" in bode_type: y_mag, y_label, mag_color = 10 * np.log10(mag_linear), '10·log|H| [dB]', Theme.ACCENT
    elif "Guadagno" in bode_type: y_mag, y_label, mag_color = 20 * np.log10(mag_linear), 'Guadagno [dB]', Theme.ACCENT
    else: y_mag, y_label, mag_color = -20 * np.log10(mag_linear), 'Attenuazione [dB]', Theme.WARNING
    
    ax_mag.plot(f_asse, y_mag, color=mag_color, lw=2.5)
    ax_mag.set_ylabel(y_label, color=Theme.TEXT_SECONDARY, fontweight='bold')
    ax_mag.set_title(f"Diagramma di Bode - {filter_obj.filter_type} {filter_obj.response_type}", color="white", fontweight='bold')
    
    ax_pha.plot(f_asse, phase_rad, color=Theme.DANGER, lw=2.5)
    ax_pha.set_ylabel('Fase ∠H(jω) [rad]', color=Theme.TEXT_SECONDARY, fontweight='bold')
    ax_pha.set_xlabel('Frequenza [Hz]', color=Theme.TEXT_SECONDARY, fontweight='bold')
    
    for ax in [ax_mag, ax_pha]:
        ax.set_facecolor('none')
        ax.grid(True, which="both", ls="-", color="white", alpha=0.1)
        for spine in ax.spines.values(): spine.set_color('none')
        ax.tick_params(colors=Theme.TEXT_SECONDARY)
        if "Lineare" not in bode_scale: ax.set_xscale('log') 
        if "Bilogaritmica" in bode_scale and "Lineare" not in bode_type: ax.set_yscale('symlog')