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

for line in lines:
    count += 1
    if "DAC-Type" in line:
        dacdepth = line.split("=")[1].replace("bit","")
    if "Gainpreamp" in line:
        preampgain = line.split("=")[1]
        print(preampgain)
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
# param = list(map(float, param))

# In Version 3, the Channel-List has to be decoded:
channellist = {
    "Current" : 1, 
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
    columnnames = ["v4", "bias", "z"]
else:
    columnnames = ["bias", "z"]

for channel in channellist:
    if int(param[3]) & channellist[channel] > 0:
        columnnames.append(channel)

print(columnnames)
data = pd.read_csv('test.VERT', delimiter='\t', skiprows=dataline+1, encoding='unicode_escape', encoding_errors='ignore', header=None,index_col=False)
fig = px.line(data)
fig.show()