from itertools import count
from venv import create
from zipapp import create_archive
import pandas as pd
import re

def get_header(filepath,filename):
    fullpath = filepath + "/" + filename
    with open(fullpath, 'r', errors="ignore") as f:
        lines = f.read().splitlines()

    lineCount = 0
    createcHeader = {
        "version": "",
        "param": "",
        "DAC-Type": 0,
        "gainpreamp": 0,
        "zpiezoconst": 0,
        "setpoint": 0,
        "biasvolt": 0,
        "dataline": 0
    }

    for line in lines:
        lineCount += 1
        if line == "DATA":
            createcHeader["dataline"] = lineCount
        else:
            for param in createcHeader:
                if param.casefold() in line.casefold():
                    createcHeader[param] = float(line.split("=")[1].replace("bit",""))

    createcHeader["biasvolt"] *= 1e-3

    # In the STMAFM-VERT files the first row has 3 numbers (+ 1 above Vers3)
    # with statistical data of the spectrum:
    # #1 Number of Points taken during Vertical Manipulation
    # #2 X Position of the Spectrum
    # #3 Y Position of the Spectrum
    # (above Vers3: #4 Number of custom DataColumns)

    createcHeader["version"] = lines[0]
    createcHeader["param"] = re.findall('([^-_\s]+)', lines[createcHeader["dataline"]])

    return createcHeader


def read_file(filepath, filename):
    fullpath = filepath + "/" + filename
    with open(fullpath, 'r', errors="ignore") as f:
        lines = f.read().splitlines()

    header = get_header(filepath, filename)
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

    if header["version"] == "[ParVERT32]":
        columnnames = ["bias", "zpos", "unknown"]
    else:
        columnnames = ["bias", "zpos"]

    for channel in channellist:
        if int(header["param"][3]) & channellist[channel] > 0:
            columnnames.append(channel)
    columnnames.append("NaN")

    ADCtoV = 20.0 / 2 ** header["DAC-Type"]
    ADCtoI = 20.0 / 2 ** header["DAC-Type"] / 10 ** (header["gainpreamp"] - 12) * 10 ** (-12)

    data = pd.read_csv(fullpath, delimiter='\t', skiprows=header["dataline"]+1, encoding='unicode_escape', encoding_errors='ignore',index_col=0,names=columnnames)
    data = data.iloc[: , :-1]
    data["current"] *= ADCtoI
    data["bias"] *= 1e-3
    data["zpos"] *= header["zpiezoconst"] / 1000 * 0.0000000001
    try:
        data["ADC2"] *= ADCtoV
    except KeyError:
        pass
    try:
        data["ADC1"] *= ADCtoV
    except KeyError:
        pass
    return data

def export(filepath,filename,columns):
    data = read_file(filepath,filename)
    exportcolumns = set(data.columns.values.tolist()).intersection(columns)

    if exportcolumns:
        outfilename = filename.replace(filename.split(".")[-1], "itx")
        outpath = filepath + "/export/" + outfilename

        with open(outpath, 'w') as outfile:
            outfile.write("IGOR\nX NewDataFolder/S "+filename.replace(filename.split(".")[-1], "").replace(".","_")[:-1]+"\nWAVES/D "+' '.join(exportcolumns)+ "\nBEGIN\n")
            data.to_csv(outfile,sep="\t",columns=exportcolumns,index=False,header=False)
            outfile.write(
                "END\n"+
                "X Setscale d, 0,0, \"V\", bias\n"+
                "X Setscale d, 0,0, \"A\", current\n"
                )