import pandas as pd
import plotly.express as px
import plotly.io as pio
import re

pio.renderers.default = "vscode"


with open('test.VERT', 'r', errors="ignore") as f:
    lines = f.readlines()

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
    if line == "DATA\n":
        dataline = count

param = re.findall('([^-_\s]+)', lines[dataline])

data = pd.read_csv('test.VERT', delimiter='\t', skiprows=dataline+1, encoding='unicode_escape', encoding_errors='ignore', header=None)
fig = px.line(data)
fig.show()