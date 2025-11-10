import numpy as np

sxmCH = {
    ":Bias>Bias (V):" : {
        "unitType": "direct",
        "unit": "V",
        "symbol": "$V$"
    },
    ":Z-Controller>Setpoint:" : {
        "unitType": "eval",
        "unit": ":Z-Controller>Setpoint unit:",
        "symbol": "$Z_{sp}$"
    },
    ":Z-Controller>I gain:": {
        "unitType": "direct",
        "unit": "m/s",
        "symbol": "$I_{FB}$"
    },
    ":Scan>speed forw. (m/s):": {
        "unitType": "direct",
        "unit": "m/s",
        "symbol": "$v$"
    },
    ":Oscillation Control>Amplitude Setpoint (m):": {
        "unitType": "direct",
        "unit": "m",
        "symbol": "$A_{osc}$",
    }
}

sxmCC = {
    ":Bias>Bias (V):" : {
        "unitType": "direct",
        "unit": "V",
        "symbol": "$V$"
    },
    ":Z-Controller>Z (m):" :{
        "unitType": "direct",
        "unit": "m",
        "symbol": "$Z$",
        "precision": 6
    },
    ":Scan>speed forw. (m/s):": {
        "unitType": "direct",
        "unit": "m/s",
        "symbol": "$v$"
    },
}

spectrum = {
    "": {
        "unitType": "direct",
        "unit": "",
        "symbol": ""
    },
    "Bias>Bias (V)" : {
        "unitType": "direct",
        "unit": "V",
        "symbol": "$V$"
    },
    "Z (m)": {
        "unitType": "direct",
        "unit": "m",
        "symbol": "$Z$",
        "precision": 6
    },
    "Lock-in>Amplitude": {
        "unitType": "direct",
        "unit": "V",
        "symbol": "$V_{mod}$"
    },
    "f_res (Hz)": {
        "unitType": "direct",
        "unit": "Hz",
        "symbol": "$f_0$",
        "precision" : 10
    },
    "Q": {
        "unitType": "direct",
        "unit": "",
        "symbol": "$Q$"
    },
    "Phase (deg)": {
        "unitType": "direct",
        "unit": "°",
        "symbol": "$\\Phi$"
    },
    "Oscillation Control>Amplitude Setpoint (m)": {
        "unitType": "direct",
        "unit": "m",
        "symbol": "$A_{osc}$",
    },
    "Sample period (ms)": {
        "unitType": "direct",
        "unit": "ms",
        "symbol": "$t_{sample}$"
    },

}

spectrumZ = {
    "Z-Controller>Setpoint" : {
        "unitType": "eval",
        "unit": "Z-Controller>Setpoint unit",
        "symbol": "$Z_{sp}$"
    }
}

grid = {
    "Bias>Bias (V)" : {
        "unitType": "direct",
        "unit": "V",
        "symbol": "$V$"
    },
    "Z (m)": {
        "unitType": "direct",
        "unit": "m",
        "symbol": "$Z$",
        "precision": 6
    },
    "Lock-in>Amplitude": {
        "unitType": "direct",
        "unit": "V",
        "symbol": "$V_{mod}$"
    },
    "f_res (Hz)": {
        "unitType": "direct",
        "unit": "Hz",
        "symbol": "$f_0$",
        "precision" : 10
    },
    "Q": {
        "unitType": "direct",
        "unit": "",
        "symbol": "$Q$"
    },
    "Phase (deg)": {
        "unitType": "direct",
        "unit": "°",
        "symbol": "$\\Phi$"
    },
    "Oscillation Control>Amplitude Setpoint (m)": {
        "unitType": "direct",
        "unit": "m",
        "symbol": "$A_{osc}$",
    },
}

def getHeaderLabels(header, dtype):
    labels = []
    if dtype == "sxm":
        if header[":Z-Controller>Controller status:"][0] == "ON":
            headerDict = sxmCH
        elif header[":Z-Controller>Controller status:"][0] == "OFF":
            headerDict = sxmCC
    elif dtype == "spectrum":
        headerDict = spectrum
        if "Z-Controller>Controller status" in header:
            if header["Z-Controller>Controller status"] == "ON":
                headerDict.update(spectrumZ)
    elif dtype == "grid":
        headerDict = grid
        if "Z-Controller>Controller status" in header:
            if header["Z-Controller>Controller status"] == "ON":
                headerDict.update(spectrumZ)
    else:
        headerDict = {}
 
    for headerKey, headerVal in headerDict.items():
        try:
            value = header[headerKey]
            if headerVal["unitType"] == "direct":
                unit = headerVal["unit"]
            elif headerVal["unitType"] == "eval":
                unit = header[headerVal["unit"]]
                if type(unit) == list:
                    unit = unit[0]
            if type(value) == list:
                value = value[0]
            try:
                prec = headerVal["precision"]
            except KeyError:
                prec = 4
            labels.append(headerVal["symbol"] + " = "+ formatSI(value,precision=prec) + unit)
        except KeyError:
            pass
    return labels

def formatSI(value, precision=4):
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