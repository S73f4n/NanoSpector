import pandas as pd
import matplotlib.pyplot as plt

with open('test.VERT', 'r', errors="ignore") as f:
    lines = f.readlines()

dataline = 0
count = 0

for line in lines:
    count += 1
    if line == "DATA\n":
        dataline = count

data = pd.read_csv('test.VERT', delimiter='\t', skiprows=dataline+1, encoding='unicode_escape', encoding_errors='ignore')
plt.plot(data)
plt.show()