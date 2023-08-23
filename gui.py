import gi
import glob
from nanonis_load import didv
import yaml
import os
import tempfile
import io
import clipboard
from si_prefix import si_format

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar
from matplotlib.ticker import EngFormatter
from matplotlib import style
import matplotlib.patches as mpl_patches

current_file = ["", ""]
data = None


class Handler:
    def __init__(self):
         self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

    def on_mainwindow_show(self, *args):
        self.read_settings()
        self.open_folder()

    def on_mainwindow_destroy(self, *args):
        self.write_settings()
        Gtk.main_quit()

    def on_selection_changed(self, folder_chooser):
        settings['file']['path'] = folder_chooser.get_filename()
        self.open_folder()

    def open_folder(self):
        store.clear()   
        header = Gtk.Builder.get_object(builder, "header_bar")
        header.set_subtitle(settings['file']['path'])
        files = []
        # treeiter = store.append(glob.glob(filepath + "/*.VERT"))
        subDir = settings['file']['path']
        files += [os.path.join(subDir, file) for file in os.listdir(subDir) if os.path.isfile(os.path.join(subDir, file)) and file.endswith(settings['file']['extension'])]
        for filename in sorted(files, key=os.path.getmtime, reverse=True):
            treeiter = store.append([filename.split("/")[-1]])
    
    def plot_data(self,plotname):
        xaxisModel, xaxisIter = Gtk.Builder.get_object(builder, "selection_xaxis").get_selected_rows()
        yaxisModel, yaxisIter = Gtk.Builder.get_object(builder, "selection_yaxis").get_selected_rows()
        if xaxisIter and yaxisIter:
            plot_multiple = Gtk.Builder.get_object(builder, "button_multiple").get_active()
            plot_log = Gtk.Builder.get_object(builder, "button_logplot").get_active()
            if not plot_multiple:
                ax.cla()
            try:
                xaxis = xaxisModel[xaxisIter][0]
                yaxis = yaxisModel[yaxisIter][0]
                xaxislabel = xaxis 
                yaxislabel = yaxis 
                # didv.plot(x=xaxis, y=yaxis,ax=ax,label=plotname,xlabel=xaxislabel,ylabel=yaxislabel)
                didv.plot(data, channel=yaxis, axes=ax,legend=False)
                if plot_log:
                    ax.set_yscale('log')
                else:
                    ax.set_yscale('linear')
                ax.set_ylabel(yaxislabel)
                ax.xaxis.set_major_formatter(formatter1)
                ax.yaxis.set_major_formatter(formatter1)
                legendLabels = self.getHeaderLabels(data) 
                handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", 
                                                lw=0, alpha=0)] * len(legendLabels)
                # create the legend, supressing the blank space of the empty line symbol and the
                # padding between symbol and label by setting handlelenght and handletextpad
                ax.legend(handles, legendLabels, loc='best', fontsize='small', 
                        fancybox=True, framealpha=1, 
                        handlelength=0, handletextpad=0)
                fig.axes[0].set_title(plotname + "\n" + data.header['Saved Date'],
                            fontsize='medium')
            except KeyError:
                pass
            fig.canvas.draw()

    def plot_all_files(self, selection):
        model, treeiter = selection.get_selected_rows()
        if treeiter:
            if len(treeiter) > 1:
                ax.cla()
            for thisiter in treeiter:
                settings['file']['name'] = model[thisiter][0]
                global data
                filename = settings['file']['path']+'/'+settings['file']['name']
                data = didv.spectrum(filename)
                self.plot_data(settings['file']['name'])
                # fileheader = createc.get_header(settings['file']['path'],settings['file']['name'])
                # self.set_header_label(fileheader)

    def on_selection_xaxis_changed(self, selection):
        ax.cla()
        self.plot_all_files(Gtk.Builder.get_object(builder, "selection_file"))

    def on_selection_yaxis_changed(self, selection):
        ax.cla()
        self.plot_all_files(Gtk.Builder.get_object(builder, "selection_file"))

    def on_file_selected(self, selection):
        self.plot_all_files(selection)

    def on_logplot_changed(self,button):
        ax.cla()
        self.plot_all_files(Gtk.Builder.get_object(builder, "selection_file"))

    def read_settings(self):
        with open("settings.yaml", "r") as settingsFile:
            global settings
            settings = yaml.safe_load(settingsFile)   
    
    def write_settings(self):
        with open('settings.yaml', 'w') as file:
            yaml.dump(settings, file)

    def on_button_clear_clicked(self, button):
        ax.cla()
        fig.canvas.draw()

    def set_header_label(self,fileheader):
        label_current = Gtk.Builder.get_object(builder, "label_current")
        label_voltage = Gtk.Builder.get_object(builder, "label_voltage")
        label_current.set_text("I = "+si_format(fileheader["setpoint"])+"A")
        label_voltage.set_text("V = "+si_format(fileheader["biasvolt"])+"V")
    
    def on_button_export_clicked(self,button):
        filemodel, fileiter = Gtk.Builder.get_object(builder, "selection_file").get_selected_rows()
        if fileiter:
            for filei in fileiter:
                columns = []
                xaxis, xaxisIter = Gtk.Builder.get_object(builder, "selection_xaxis").get_selected_rows()
                yaxis, yaxisIter = Gtk.Builder.get_object(builder, "selection_yaxis").get_selected_rows()
                for treeiter in xaxisIter:
                    columns.append(xaxis[treeiter][0])
                for treeiter in yaxisIter:
                    columns.append(yaxis[treeiter][0])
                createc.export(settings['file']['path'],filemodel[filei][0],columns)

    def on_button_savefig_clicked(self,button):
        filemodel, fileiter = Gtk.Builder.get_object(builder, "selection_file").get_selected_rows()
        savefig = io.BytesIO()
        if fileiter:
            savefig.name = settings['file']['path'] + "/export/" + filemodel[fileiter][0].replace(filemodel[fileiter][0].split(".")[-1], "png")
            fig.savefig(savefig.name, dpi=300,format='png',bbox_inches='tight')
            savefig.seek(0)
            piximage = Gtk.Image.new_from_file(savefig.name)
            self.clipboard.set_image(piximage.get_pixbuf())

    def getHeaderLabels(self, data):
            labels = [] 
            try:
                labels.append("V = " + self.formatSI(data.header['Bias>Bias (V)']) + "V")
            except KeyError:
                pass
            try: 
                labels.append("Z = " + self.formatSI(data.header['Z (m)']) + "m")
            except KeyError:
                pass
            try: 
                labels.append("$I$ = " + self.formatSI(data.header['Current>Current (A)']) + "A")
            except KeyError:
                pass
            try: 
                labels.append("$V_{mod}$ = " + self.formatSI(data.header['Lock-in>Amplitude']) + "V")
            except KeyError:
                pass
            try: 
                labels.append("$f_0$ = " + self.formatSI(data.header['f_res (Hz)'],precision=10) + "Hz")
            except KeyError:
                pass
            try: 
                labels.append("$Q$ = " + str(data.header['Q']))
            except KeyError:
                pass
            try: 
                labels.append("$\Phi$ = " + self.formatSI(data.header['Phase (deg)']) + "°")
            except KeyError:
                pass
            try:
                labels.append("$V$ = " + self.formatSI(data.header[':Bias>Bias (V):'][0]) + "V")
            except KeyError:
                pass
            try:
                labels.append("$I$ =" + self.formatSI(data.header[':Current>Current (A):'][0]) + "A")
            except KeyError:
                pass
            try:
                labels.append("$Z$ = " + self.formatSI(data.header[':Z-Controller>Setpoint:'][0]) + data.header[':Z-Controller>Setpoint unit:'][0])
            except KeyError:
                pass
            try:
                labels.append("$I_{FB}$ = " + self.formatSI(data.header[':Z-Controller>I gain:'][0]) + 'm/s')
            except KeyError:
                pass
            try:
                labels.append("$v$ = " + self.formatSI(data.header[':Scan>speed forw. (m/s):'][0]) + "m/s")
            except KeyError:
                pass
            return labels

    def formatSI(self, value, precision=3):
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
        exponent = int(np.floor(np.log10(np.abs(value))))
        exponent = (exponent // 3) * 3  # Round to the nearest multiple of 3
        scaled_value = value / 10**exponent

        return f"{scaled_value:.{precision}g} {prefixes[exponent]}"


builder = Gtk.Builder()
builder.add_from_file("main.glade")
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
sw = builder.get_object('scrolledwindow1')
swtoolbar = builder.get_object('scrolledwindow2')

# fig = Figure(figsize=(4,3), dpi=100)
# ax = fig.add_subplot()
plt.style.use('bmh')
fig, ax = plt.subplots()
# fig.tight_layout()
formatter1 = EngFormatter(places=2, sep="\u2009")
canvas = FigureCanvas(fig)
toolbar = NavigationToolbar(canvas, window)
sw.add_with_viewport(canvas)
swtoolbar.add_with_viewport(toolbar)

window.show_all()
Gtk.main()