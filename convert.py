import pandas as pd
import plotly.express as px
import plotly.io as pio
import re

pio.renderers.default = "vscode"

with open('test.VERT', 'r', errors="ignore") as f:
    lines = f.read().splitlines()

dataline = 0
count = 0
dacdepth = 0
preampgain = 0
zpiezoconst = 0

for line in lines:
    count += 1
    if "DAC-Type" in line:
        dacdepth = int(line.split("=")[1].replace("bit",""))
    if "Gainpreamp" in line:
        preampgain = int(line.split("=")[1])
    if "ZPiezoconst" in line:
        zpiezoconst = float(line.split("=")[1])
    if line == "DATA":
        dataline = count

# In the STMAFM-VERT files the first row has 3 numbers (+ 1 above Vers3)
# with statistical data of the spectrum:
# #1 Number of Points taken during Vertical Manipulation
# #2 X Position of the Spectrum
# #3 Y Position of the Spectrum
# (above Vers3: #4 Number of custom DataColumns)

version = lines[0]
param = re.findall('([^-_\s]+)', lines[dataline])

# In Version 3, the Channel-List has to be decoded:
channellist = {
    "current" : 1, 
    "dI/dV"   : 2, 
    "d2I/dV2" : 4, 
    "ADC0"    : 8, 
    "ADC1"    : 16,
    "ADC2"    : 32,
    "ADC3"    : 64,
    ""       : 128, 
    ""       : 256, 
    ""      : 512, 
    "di_q"    : 1024,
    "di2_q"   : 2048,
    "Top DAC0": 4096,
}

if version == "[ParVERT32]":
    columnnames = ["bias", "z", "unknown"]
else:
    columnnames = ["bias", "z"]

for channel in channellist:
    if int(param[3]) & channellist[channel] > 0:
        columnnames.append(channel)
columnnames.append("NaN")

ADCtoV = 20.0 / 2 ** dacdepth
ADCtoI = 20.0 / 2 ** dacdepth / 10 ** (preampgain - 12) * 10 ** (-12)

data = pd.read_csv('test.VERT', delimiter='\t', skiprows=dataline+1, encoding='unicode_escape', encoding_errors='ignore',index_col=0,names=columnnames)
data = data.iloc[: , :-1]
data["current"] *= ADCtoI
data["bias"] *= 1e-3
data["ADC1"] *= ADCtoV
data["ADC2"] *= ADCtoV
data["z"] *= zpiezoconst / 1000 * 0.0000000001


print(data)
fig = px.line(data, x="bias", y=["current", "ADC1", "ADC2"])
fig.show()