#!/usr/bin/env python
import gi
import nanonis_load
from nanonis_load import didv, sxm
import yaml
import os
import io
from si_prefix import si_format
import warnings

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

class Handler:
    def __init__(self):
         self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
         self.datastore = []
         self.selectedRows = []

    def on_mainwindow_show(self, *args):
        self.read_settings()
        self.open_folder()

    def on_mainwindow_destroy(self, *args):
        self.write_settings()
        Gtk.main_quit()

    def on_selection_changed(self, folder_chooser):
        settings['file']['path'] = folder_chooser.get_filename()
        self.open_folder()

    def setChannelList(self, channelList):
        selection = Gtk.Builder.get_object(builder, "selection_yaxis")
        selection.handler_block_by_func(self.on_selection_yaxis_changed)
        # selection.unselect_all()
        ylistData = [list(row)[0] for row in yaxisList]
        if len(ylistData) == len(channelList):
            refreshList = not all(row in ylistData for row in channelList) 
        else:
            refreshList = True
        if refreshList:
            yaxisList.clear()
            for ch in channelList:
                model = yaxisList.append([ch])
            self.selectedRows = []
        selection.handler_unblock_by_func(self.on_selection_yaxis_changed)

    def on_refresh_clicked(self, button):
        self.open_folder()

    def open_folder(self):
        store.clear()   
        header = Gtk.Builder.get_object(builder, "header_bar")
        header.set_subtitle(settings['file']['path'])
        files = []
        # treeiter = store.append(glob.glob(filepath + "/*.VERT"))
        subDir = settings['file']['path']
        files += [os.path.join(subDir, file) for file in os.listdir(subDir) if os.path.isfile(os.path.join(subDir, file)) and (file.endswith(settings['spec']['extension']) or file.endswith(settings['image']['extension']))]
        for filename in sorted(files, key=os.path.getmtime, reverse=True):
            treeiter = store.append([os.path.basename(filename)])
    
    def plot_data(self):
        plot_log = Gtk.Builder.get_object(builder, "button_logplot").get_active()
        flatten = Gtk.Builder.get_object(builder, "button_flatten").get_active()
        plane = Gtk.Builder.get_object(builder, "button_plane").get_active()
        ax.cla()
        try:
            # xaxis = xaxisModel[xaxisIter][0]#
            selected_rows = []
            legendLabels = []
            for data in self.datastore:
                if isinstance(data,nanonis_load.didv.spectrum):
                    if self.selectedRows == []:
                        selected_rows.append(settings['spec']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    yaxislabel = selected_rows[0]
                    for ch in selected_rows:
                        didv.plot(data, channel=ch, axes=ax,legend=False)
                    ax.autoscale(enable=True,axis='both')
                    if plot_log:
                        try: 
                            ax.set_yscale('log')
                        except UserWarning:
                            ax.set_yscale('linear')
                    else:
                        ax.set_yscale('linear')
                    ax.set_ylabel(yaxislabel)
                    ax.set_aspect('auto')
                    ax.xaxis.set_major_formatter(formatter1)
                    ax.yaxis.set_major_formatter(formatter1)
                    plotname = data._filename
                    alpha = 1
                    loc = 'best'
                    if len(self.datastore) > 1:
                        legendLabels.append(os.path.basename(plotname))
                        handles = None
                    elif len(selected_rows) > 1:
                        legendLabels = selected_rows.copy() 
                        handles = None
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header['Saved Date'], fontsize='medium')
                        ax.annotate('\n'.join(self.getHeaderLabels(data)),xy=(0.015,0.8),fontsize='small',xycoords='axes fraction',bbox=dict(alpha=0.7, facecolor='#eeeeee', edgecolor='#bcbcbc', linewidth=0.5,pad=3))
                    else:
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header['Saved Date'], fontsize='medium')
                        legendLabels = self.getHeaderLabels(data) 
                        handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * len(legendLabels)
                if isinstance(data,nanonis_load.sxm.sxm):
                    if self.selectedRows == []:
                        selected_rows.append(settings['image']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    yaxislabel = selected_rows[0]
                    sxm.plot(data, channel=selected_rows[0],flatten=flatten,subtract_plane=plane,axes=ax)
                    # fig.delaxes(fig.axes[1])
                    # fig.axes[1].remove()
                    xmax=fig.axes[0].get_xticks()[-1]
                    ymax=fig.axes[0].get_yticks()[-1]
                    alpha = 0.4
                    loc = 'lower right'
                    plotname = data.filename
                    fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header[':REC_DATE:'][0] + " " +  data.header[':REC_TIME:'][0] + '\n{:g} x {:g} nm'.format(xmax,ymax),
                                fontsize='small')
                    fig.axes[0].axis('off')            
                    # fig.set_figwidth(8)
                    legendLabels = self.getHeaderLabels(data) 
                    handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * len(legendLabels)
                if handles == None:
                    ax.legend(legendLabels,loc=loc,fontsize='small',fancybox=True,framealpha=alpha)
                else:
                    ax.legend(handles, legendLabels, loc=loc, fontsize='small', fancybox=True, framealpha=alpha, handlelength=0, handletextpad=0)
        except KeyError:
            pass
        fig.canvas.draw()

    def getDataFromFiles(self, files):
        self.datastore = []
        for thisFile in files:
            filename = os.path.join(settings['file']['path'],thisFile)
            if filename.endswith('.dat'):
                self.datastore.append(didv.spectrum(filename))
            if filename.endswith('.sxm'):
                self.datastore.append(sxm.sxm(filename))
            self.setChannelList(self.datastore[-1].data.keys())

    def on_selection_yaxis_changed(self,selection):
        yaxisModel, yaxisIter = selection.get_selected_rows()
        if yaxisIter:
            ax.cla()
            self.selectedRows = []
            for yiter in yaxisIter:
                self.selectedRows.append(yaxisModel[yiter][0])
        self.plot_data()

    def on_file_selected(self, selection):
        model, treeiter = selection.get_selected_rows()
        files = []
        if treeiter:
            for thisiter in treeiter:
                files.append(model[thisiter][0])
        self.getDataFromFiles(files)
        self.plot_data()

    def on_logplot_changed(self,button):
        ax.cla()
        self.plot_data()

    def read_settings(self):
        with open(os.path.join(os.path.dirname(__file__),"settings.yaml"), "r") as settingsFile:
            global settings
            settings = yaml.safe_load(settingsFile)   
    
    def write_settings(self):
        with open(os.path.join(os.path.dirname(__file__), "settings.yaml"), 'w') as file:
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
        os.makedirs(os.path.join(settings['file']['path'],"export"), exist_ok=True)
        if fileiter:
            savefig.name = os.path.join(settings['file']['path'], "export", filemodel[fileiter][0].replace(os.path.splitext(filemodel[fileiter][0])[1],".png"))
            fig.savefig(savefig.name, dpi=300,format='png',bbox_inches='tight')
            savefig.seek(0)
            piximage = Gtk.Image.new_from_file(savefig.name)
            self.clipboard.set_image(piximage.get_pixbuf())
            fig.canvas.draw()

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
builder.add_from_file(os.path.join(os.path.dirname(__file__),"main.glade"))
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
yaxisList = builder.get_object("yaxis_list")
sw = builder.get_object('scrolledwindow1')
swtoolbar = builder.get_object('scrolledwindow2')

# fig = Figure(figsize=(4,3), dpi=100)
# ax = fig.add_subplot()
plt.style.use('bmh')
fig, ax = plt.subplots()
# fig.tight_layout()
formatter1 = EngFormatter(sep="\u2009")
canvas = FigureCanvas(fig)
toolbar = NavigationToolbar(canvas, window)
sw.add(canvas)
swtoolbar.add(toolbar)

warnings.filterwarnings("error")

window.show_all()
Gtk.main()