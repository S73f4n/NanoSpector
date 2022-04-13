import gi
import glob
import createc
from si_prefix import si_format

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


from matplotlib.figure import Figure
import numpy as np
import matplotlib.cm as cm
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
from matplotlib.ticker import EngFormatter

current_file = ["", ""]
data = None

def plot_data(plotname):
    channel_units = {
        "bias": "V",
        "zpos": "m",
        "current": "A",
        "ADC0": "V",
        "ADC1": "V",
        "ADC2": "V",
        "ADC3": "V",
        "dI/dV": "V/A",
    }
    xaxisModel, xaxisIter = Gtk.Builder.get_object(builder, "selection_xaxis").get_selected_rows()
    yaxisModel, yaxisIter = Gtk.Builder.get_object(builder, "selection_yaxis").get_selected_rows()
    if xaxisIter and yaxisIter:
        plot_multiple = Gtk.Builder.get_object(builder, "button_multiple").get_active()
        if not plot_multiple:
            ax.cla()
        try:
            xaxis = xaxisModel[xaxisIter][0]
            yaxis = yaxisModel[yaxisIter][0]
            xaxislabel = xaxis + " (" + channel_units[xaxis] + ")"
            yaxislabel = yaxis + " (" + channel_units[yaxis] + ")"
            data.plot(x=xaxis, y=yaxis,ax=ax,label=plotname,xlabel=xaxislabel,ylabel=yaxislabel)
            ax.xaxis.set_major_formatter(formatter1)
            ax.yaxis.set_major_formatter(formatter1)
        except KeyError:
            pass
        fig.canvas.draw()
class Handler:
    def on_mainwindow_destroy(self, *args):
        Gtk.main_quit()

    def on_button1_clicked(self, button):
        print("Hello World!")
        data.plot(x="bias", y="current",ax=ax)
        fig.canvas.draw()
    
    def on_current_folder_changed(self, folder_chooser):
        print("Folder:" + folder_chooser.get_filename())

    def on_selection_changed(self, folder_chooser):
        filepath = folder_chooser.get_filename()
        header = Gtk.Builder.get_object(builder, "header_bar")
        header.set_subtitle(filepath)
        # treeiter = store.append(glob.glob(filepath + "/*.VERT"))
        for filename in sorted(glob.glob(filepath + "/*.VERT")):
            treeiter = store.append([filename.split("/")[-1]])
        current_file[0] = filepath

    def plot_all_files(self, selection):
        model, treeiter = selection.get_selected_rows()
        if treeiter:
            if len(treeiter) > 1:
                ax.cla()
            for thisiter in treeiter:
                filename = model[thisiter][0]
                current_file[1] = filename
                global data
                data = createc.read_file(current_file[0],filename)
                plot_data(filename)
                fileheader = createc.get_header(current_file[0],filename)
                self.set_header_label(fileheader)

    def on_selection_xaxis_changed(self, selection):
        ax.cla()
        self.plot_all_files(Gtk.Builder.get_object(builder, "selection_file"))

    def on_selection_yaxis_changed(self, selection):
        ax.cla()
        self.plot_all_files(Gtk.Builder.get_object(builder, "selection_file"))

    def on_file_selected(self, selection):
        self.plot_all_files(selection)

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
                createc.export(current_file[0],filemodel[filei][0],columns)

builder = Gtk.Builder()
builder.add_from_file("main.glade")
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
sw = builder.get_object('scrolledwindow1')

fig = Figure(figsize=(4,3), dpi=100)
ax = fig.add_subplot()
formatter1 = EngFormatter(places=0, sep="\u2009")
canvas = FigureCanvas(fig)
sw.add(canvas)

window.show_all()
Gtk.main()