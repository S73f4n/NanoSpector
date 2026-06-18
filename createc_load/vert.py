import pandas as pd
from .channellist import param30chlist, param32chlist, dacUnits 

import matplotlib
import matplotlib.animation
import matplotlib.pyplot as plt

import numpy as np
from matplotlib import cm

class Spectrum:
    def __init__(self, filename=None, attribute=None):

        self.header = {}
        if filename is None:
            return
        self._filename = filename
        with open(filename, "r", errors="ignore") as file_id:
            self.version = file_id.readline().strip()
            header_lines = 2
            while True:
                file_line = file_id.readline().strip()
                if file_line == "DATA":
                    self.params = file_id.readline().split()
                    break
                header_lines += 1
                file_line = file_line.split("=")
                if len(file_line) > 1:
                    self.header[file_line[0]] = file_line[1].strip()
            # self._fix_header()
            if attribute is not None:
                self.header["attribute"] = attribute


        # self.data = pd.read_csv(
        #     filename, sep="\t", header=header_lines, skip_blank_lines=False
        # )

        self.data = pd.read_csv(
            filename, 
            delimiter='\t', 
            skiprows=header_lines+1, 
            encoding='unicode_escape', 
            encoding_errors='ignore',
            header=None,
            index_col=0
            )

        self.data = self.data.dropna(axis=1,how="all")

        self._make_channel_names()

    def _make_channel_names(self):
        columnnames = []
        if self.version == "[ParVERT32]":
            channellist = param32chlist

            if self.params[6] == 3:
                columnnames = ["Bias (V)", "Z (nm)", "X (nm)"]
            elif self.params[6] == 2:
                columnnames = ["Bias (V)", "Z (nm)"]
            else:
                columnnames = ["Bias (V)", "Z (nm)", "unknown"]

            for channel in channellist:
                if int(self.params[3]) & channellist[channel] > 0:
                    columnnames.append(channel)

        elif self.version == "[ParVERT30]":
            channellist = param30chlist

            columnnames = ["Bias (V)", "Z (nm)"]
            for channel in channellist:
                if int(self.params[3]) & channellist[channel] > 0:
                    columnnames.append(channel)


        extra_names = [
            f"extra_{i}"
            for i in range(len(columnnames), self.data.shape[1])
        ]

        self.data.columns = columnnames[:self.data.shape[1]] + extra_names
        self.data.drop(columns=extra_names,inplace=True)
        self._set_data_units()

    def _set_data_units(self):
        DACtype = float(self.header["DAC-Type"].replace("bit",""))
        ADCtoV = 20.0 / 2 ** DACtype
        ADCtoI = 20.0 / 2 ** DACtype / 10 ** (float(self.header["Gainpreamp / GainPre 10^"]) - 12) * 10 ** (-12)
        try:
            ADCtoAA = 20.0 / 2 ** DACtype * float(self.header["ZPiezoconst / ZPiezoconst"]) * float(self.header["GainZ / GainZ"])
        except KeyError:
            try:
                ADCtoAA = 20.0 / 2 ** DACtype * float(self.header["ZPiezoconst"]) * float(self.header["GainZ / GainZ"])
            except KeyError:
                pass

        for ch in self.data.keys():
            try:
                if dacUnits[ch] == "ADCI":
                    self.data[ch] *= ADCtoI
                elif dacUnits[ch] == "ADCV":
                    self.data[ch] *= ADCtoV
                elif dacUnits [ch] == "ADCZ":
                    self.data[ch] *= ADCtoAA
                elif dacUnits[ch] == "V":
                    self.data[ch] *= 1e-3
            except KeyError:
                print(f"Channel {ch} not defined!")

    def _fix_header(self):
        # if "X (m)" in self.header:
        #     self.header["x (nm)"] = float(self.header["X (m)"]) * 1e9
        # if "Y (m)" in self.header:
        #     self.header["y (nm)"] = float(self.header["Y (m)"]) * 1e9
        # if "Z (m)" in self.header:
        #     self.header["z (nm)"] = float(self.header["Z (m)"]) * 1e9
        # if "Gate Voltage (V)" in self.header:
        #     self.header["Gate (V)"] = float(self.header["Gate Voltage (V)"])
        #     self.gate = self.header["Gate (V)"]
        pass


class Plot:
    r"""
    Plots a list of didv.spectra. Each spectrum is plotted a separate line.

    Args:
        spectra : List[didv.spectra]
            List of didv.spectra to be plotted.
        channel: str (defaults to 'Input 2 (V)')
            The x-axis is 'Bias calc (V)'. The y-axis is channel.
        waterfall: float (default is 0)
            Offset each curve vertically by waterfall.
            To use waterfall, you must also specify increment.
        increment: Optional[float]
            The sign of increment determines whether waterfall shifts the spectra
            in ascending order or descending order.
        multiply : Optional[float]
            If not None, scale the data by a multiplicative factor.
        color : list of colors or a cmap-like object that matplotlib will accept
            Determines the color of each spectrum line.

    Attributes:
        fig : the matplotlib figure object
        ax : the matplotlib axes object

    Methods:
        xlim(x_min : float, x_max : float) : None
            Set the x-axis limits. x_min < x_max
        ylim(y_min : float, y_max : float) : None
            Set the y-axis limits. y_min < y_max
    """

    def __init__(
        self,
        spectra,
        channel="Input 2 (V)",
        names=None,
        use_attributes=False,
        start=None,
        increment=None,
        waterfall=0.0,
        dark=False,
        multiply=None,
        average = None,
        logabs = False,
        plot_on_previous=False,
        axes=None,
        color=None,
        bias_shift=0,
        gate_as_index=True,
        legend=True,
        **kwargs,
    ):

        if plot_on_previous:
            self.ax = plt.gca()
            self.fig = self.ax.figure
        elif axes is not None:
            self.ax = axes
            self.fig = self.ax.figure
        else:
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111)
        name_list = names

        if (start is not None) and (increment is not None):
            name_list = (
                np.arange(len(spectra)) * increment + start
            )  # Does not work if spectra is a non-list iterator
        try:
            spectra_iterator = iter(spectra)
        except TypeError:
            spectra_iterator = iter([spectra])
        for idx, spectrum_inst in enumerate(spectra_iterator):
            try:
                if use_attributes:
                    spectrum_label = str(spectrum_inst.header["attribute"])
                else:
                    spectrum_label = str(name_list[idx])
            except (TypeError, IndexError):
                spectrum_label = str(idx)
            if ("Gate (V)" in spectrum_inst.header) and (gate_as_index):
                spectrum_label = str(spectrum_inst.header["Gate (V)"])
            spec_data = spectrum_inst.data.copy()
            if average is not None:
                spec_data[channel] = np.average(np.array([spec_data[channel], spec_data[average]]), axis=0)
            if multiply is not None:
                spec_data[channel] = multiply + spec_data[channel]
            if logabs:
                spec_data[channel] = abs(spec_data[channel])

            plot_args = dict(
                    x=spec_data.columns[0],
                    y=channel,
                    ax=self.ax,
                    legend=False,
                    label=spectrum_label,
                )

            if self._is_unique(spec_data[spec_data.columns[0]]):
                plot_args["x"] = spec_data.columns[1]

            if bias_shift != 0:
                spec_data.iloc[:, 0] -= bias_shift
            spec_data.plot(**plot_args)

        # Make a legend
        if legend:
            box = self.ax.get_position()
            self.ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
            if (waterfall == 0) or (np.sign(increment) < 0):
                self.legend = self.ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
                plot_lines = self.ax.get_lines()
            else:
                handles, labels = self.ax.get_legend_handles_labels()
                self.legend = self.ax.legend(
                    handles[::-1],
                    labels[::-1],
                    loc="center left",
                    bbox_to_anchor=(1, 0.5),
                )
                plot_lines = self.ax.get_lines()
                plot_lines.reverse()
            legend_lines = self.legend.get_lines()
            line_map = dict()
            for legend_line, plot_line in zip(legend_lines, plot_lines):
                legend_line.set_picker(True)
                legend_line.set_pickradius(5)
                line_map[legend_line] = plot_line

            def pick_line(event):
                legend_line = event.artist
                plot_line = line_map[legend_line]
                visibility = not plot_line.get_visible()
                plot_line.set_visible(visibility)
                if visibility:
                    legend_line.set_alpha(1)
                else:
                    legend_line.set_alpha(0.2)
                self.fig.canvas.draw()

            self.pick_line = pick_line
            self.fig.canvas.mpl_connect("pick_event", pick_line)

        if dark:
            plt.style.use("default")

    def xlim(self, x_min, x_max):
        self.ax.set_xlim(x_min, x_max)

    def ylim(self, y_min, y_max):
        self.ax.set_ylim(y_min, y_max)

    def _is_unique(self, s):
        arr = s.to_numpy()
        return (arr[0] == arr).all()
