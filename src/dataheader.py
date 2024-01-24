import numpy as np

def getHeaderLabels(data):
        labels = [] 
        try:
            labels.append("V = " + formatSI(data.header['Bias>Bias (V)']) + "V")
        except KeyError:
            pass
        try:
            labels.append("Sample period = " + str(data.header['Sample Period (ms)']) + " ms")
        except KeyError:
            pass
        try: 
            labels.append("Z = " + formatSI(data.header['Z (m)']) + "m")
        except KeyError:
            pass
        try: 
            labels.append("Z offset = " + formatSI(data.header['Z offset (m)']) + "m")
        except KeyError:
            pass
        try: 
            labels.append("$I$ = " + formatSI(data.header['Current>Current (A)']) + "A")
        except KeyError:
            pass
        try: 
            labels.append("$V_{mod}$ = " + formatSI(data.header['Lock-in>Amplitude']) + "V")
        except KeyError:
            pass
        try: 
            labels.append("$f_0$ = " + formatSI(data.header['f_res (Hz)'],precision=10) + "Hz")
        except KeyError:
            pass
        try: 
            labels.append("$Q$ = " + str(data.header['Q']))
        except KeyError:
            pass
        try: 
            labels.append("$\Phi$ = " + formatSI(data.header['Phase (deg)']) + "°")
        except KeyError:
            pass
        try:
            labels.append("$V$ = " + formatSI(data.header[':Bias>Bias (V):'][0]) + "V")
        except KeyError:
            pass
        try:
            labels.append("$I$ =" + formatSI(data.header[':Current>Current (A):'][0]) + "A")
        except KeyError:
            pass
        try:
            labels.append("$Z$ = " + formatSI(data.header[':Z-Controller>Setpoint:'][0]) + data.header[':Z-Controller>Setpoint unit:'][0])
        except KeyError:
            pass
        try:
            labels.append("$I_{FB}$ = " + formatSI(data.header[':Z-Controller>I gain:'][0]) + 'm/s')
        except KeyError:
            pass
        try:
            labels.append("$v$ = " + formatSI(data.header[':Scan>speed forw. (m/s):'][0]) + "m/s")
        except KeyError:
            pass
        try:
            labels.append("OC input = " + formatSI(data.header['Oscillation Control>Amplitude Setpoint (m)']) + "m")
        except KeyError:
            pass
        return labels
                    
def formatSI(value, precision=3):
    prefixes = {
        9: "G",   # giga
        6: "M",   # mega
        3: "k",   # kilo
        0: "",    # no prefix
        -3: "m",  # milli
        -6: "µ",  # micro
        -9: "n",  # nano
        -12: "p", # pico
        -15: "f", # femto
    }
    if type(value) == str:
        value = float(value.replace(',','.'))
    if value != 0:
        exponent = int(np.floor(np.log10(np.abs(value))))
        exponent = (exponent // 3) * 3  # Round to the nearest multiple of 3
        scaled_value = value / 10**exponent
    else:
        scaled_value = value
        exponent = 0

    return f"{scaled_value:.{precision}g} {prefixes[exponent]}"