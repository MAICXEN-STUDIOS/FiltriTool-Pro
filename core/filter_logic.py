import math
import numpy as np
import scipy.signal as signal

class FilterSynthesizer:
    def __init__(self, filter_type, response_type, spec_type, fp, fs, ap, As, R_load, first_element, f_center=1000):
        self.filter_type = filter_type 
        self.response_type = response_type 
        self.spec_type = spec_type 
        self.fp = float(fp)
        self.fs = float(fs)
        self.ap = float(ap)
        self.As = float(As)
        self.R_load = float(R_load)
        self.first_element = first_element
        self.f_center = float(f_center)
        
        self.N = 0
        self.f0 = 0.0 
        self.B0 = 0.0 
        self.gk = [] 
        self.network = [] 

    def calc_butterworth_gk(self, N):
        gk = [2 * math.sin(((2 * k - 1) * math.pi) / (2 * N)) for k in range(1, N + 1)]
        gk.append(1.0)
        return gk

    def calc_chebyshev_gk(self, N, ap):
        eps = math.sqrt(10**(ap/10) - 1)
        beta = math.log(1.0 / eps + math.sqrt(1.0 / eps**2 + 1))
        gamma = math.sinh(beta / N)
        a = [math.sin(((2*k - 1)*math.pi)/(2*N)) for k in range(1, N+1)]
        b = [gamma**2 + (math.sin((k*math.pi)/N))**2 for k in range(1, N+1)]
        
        gk = []
        for k in range(1, N+1):
            if k == 1: gk.append(2 * a[0] / gamma)
            else: gk.append((4 * a[k-2] * a[k-1]) / (b[k-2] * gk[-1]))
        gk.append(1.0 / (math.tanh(beta/4)**2) if N % 2 == 0 else 1.0)
        return gk

    def synthesize(self):
        # --- PROTEZIONI MATEMATICHE (Previene crash per input temporaneamente errati) ---
        if self.fp == self.fs: self.fs += 0.001
        if self.ap >= self.As: self.As = self.ap + 0.1
        self.fp = max(self.fp, 1e-9)
        self.fs = max(self.fs, 1e-9)
        self.f_center = max(self.f_center, 1e-9)
        
        # 1. Selettività
        if self.response_type in ["LP", "HP"]:
            self.K = self.fp / self.fs if self.response_type == "HP" else self.fs / self.fp
        else: # BP, BS
            self.K = self.fp / self.fs 
            
        if self.K == 1.0: self.K = 1.0001 # Previene divisione per zero nel log10
            
        num = max(1e-9, 10**(self.ap/10) - 1)
        den = max(1e-9, 10**(self.As/10) - 1)
        self.K1 = math.sqrt(num / den)

        # 2. Ordine N e Calcolo Banda/Taglio con Sovraspecifica
        if self.filter_type == "Butterworth":
            try:
                N_exact = abs(math.log10(self.K1) / math.log10(self.K))
            except ZeroDivisionError:
                N_exact = 1.0
                
            self.N = max(1, math.ceil(N_exact)) # Forza SEMPRE un intero >= 1
            
            val_pass = self.fp / (num**(1/(2*self.N)))
            val_stop = self.fs / (den**(1/(2*self.N)))
            
            if self.response_type in ["LP", "HP"]:
                self.f0 = val_stop if self.spec_type == "pass" else val_pass
            else:
                self.B0 = val_stop if self.spec_type == "pass" else val_pass
                
            self.gk = self.calc_butterworth_gk(self.N)

        elif self.filter_type == "Chebyshev":
            ratio = 1/self.K if self.K < 1 else self.K
            try:
                N_exact = math.acosh(1/self.K1) / math.acosh(ratio)
            except ValueError:
                N_exact = 1.0
                
            self.N = max(1, math.ceil(abs(N_exact)))
            
            if self.response_type in ["LP", "HP"]: self.f0 = self.fp
            else: self.B0 = self.fp
            self.gk = self.calc_chebyshev_gk(self.N, self.ap)
            
        else:
            self.N = 3; self.f0 = self.fp; self.B0 = self.fp
            self.gk = self.calc_butterworth_gk(3)

        self.generate_physical_network()
        return {
            "N": self.N, "f0": self.f0, "B0": self.B0, "K": self.K, "K1": self.K1,
            "gk": self.gk, "network": self.network
        }

    def generate_physical_network(self):
        self.network = []
        w0_center = 2 * math.pi * self.f_center
        w_cut = 2 * math.pi * abs(self.f0)
        B_rad = 2 * math.pi * abs(self.B0)
        
        k_amp = self.R_load
        current_type = self.first_element 
        
        for i in range(self.N):
            g = self.gk[i]
            comp = {"id": i+1, "norm_val": g}
            
            if self.response_type == "LP":
                if current_type == "L":
                    comp["type"] = "L_series"
                    comp["val"] = (g * k_amp) / w_cut
                else:
                    comp["type"] = "C_shunt"
                    comp["val"] = g / (w_cut * k_amp)
                    
            elif self.response_type == "HP":
                if current_type == "L":
                    comp["type"] = "C_series"
                    comp["val"] = 1.0 / (g * k_amp * w_cut)
                else:
                    comp["type"] = "L_shunt"
                    comp["val"] = k_amp / (g * w_cut)
                    
            elif self.response_type == "BP":
                if current_type == "L":
                    comp["type"] = "LC_series_series"
                    comp["val_L"] = (k_amp * g) / B_rad
                    comp["val_C"] = B_rad / (k_amp * (w0_center**2) * g)
                else:
                    comp["type"] = "LC_shunt_parallel"
                    comp["val_C"] = g / (k_amp * B_rad)
                    comp["val_L"] = (k_amp * B_rad) / ((w0_center**2) * g)

            elif self.response_type == "BS":
                if current_type == "L":
                    comp["type"] = "LC_series_parallel"
                    comp["val_L"] = (k_amp * B_rad * g) / (w0_center**2)
                    comp["val_C"] = 1.0 / (k_amp * B_rad * g)
                else:
                    comp["type"] = "LC_shunt_series"
                    comp["val_C"] = (B_rad * g) / (k_amp * (w0_center**2))
                    comp["val_L"] = k_amp / (B_rad * g)
                    
            self.network.append(comp)
            current_type = "C" if current_type == "L" else "L"

    def get_transfer_function(self):
        btype = self.response_type.lower()
        if btype == 'bs': btype = 'bandstop'
        if btype == 'bp': btype = 'bandpass'

        # Protezione finale sulle frequenze di taglio
        if self.response_type in ["LP", "HP"]:
            Wn = 2 * math.pi * max(1e-9, abs(self.f0))
        else: 
            # Calcolo frequenze di taglio asimmetriche garantendo valori positivi
            flo = (-abs(self.B0) + math.sqrt(self.B0**2 + 4*(self.f_center**2))) / 2
            fhi = flo + abs(self.B0)
            Wn = [2 * math.pi * max(1e-9, flo), 2 * math.pi * max(1e-9, fhi)]

        if self.filter_type == "Butterworth":
            b, a = signal.butter(self.N, Wn, btype=btype, analog=True)
        elif self.filter_type == "Chebyshev":
            b, a = signal.cheby1(self.N, self.ap, Wn, btype=btype, analog=True)
        else:
            b, a = signal.bessel(self.N, Wn, btype=btype, analog=True)
            
        return b, a