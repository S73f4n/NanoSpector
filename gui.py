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

current_file = ["", ""]
data = None

def plot_data():
    xaxis, xaxisIter = Gtk.Builder.get_object(builder, "selection_xaxis").get_selected_rows()
    yaxis, yaxisIter = Gtk.Builder.get_object(builder, "selection_yaxis").get_selected_rows()
    if xaxisIter and yaxisIter:
        plot_multiple = Gtk.Builder.get_object(builder, "button_multiple").get_active()
        if not plot_multiple:
            ax.cla()
        data.plot(x=xaxis[xaxisIter][0], y=yaxis[yaxisIter][0],ax=ax)
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
        print("Folder:" + filepath)
        header = Gtk.Builder.get_object(builder, "header_bar")
        header.set_subtitle(filepath)
        # treeiter = store.append(glob.glob(filepath + "/*.VERT"))
        for filename in sorted(glob.glob(filepath + "/*.VERT")):
            treeiter = store.append([filename.split("/")[-1]])
        current_file[0] = filepath

    def on_file_selected(self, selection):
        model, treeiter = selection.get_selected_rows()
        if treeiter is not None:
            filename = model[treeiter][0]
            current_file[1] = filename
            print("You selected", filename)
            global data
            data = createc.read_file(current_file[0],current_file[1])
            plot_data()
            fileheader = createc.get_header(current_file[0],current_file[1])
            self.set_header_label(fileheader)

    def on_button_clear_clicked(self, button):
        ax.cla()
        fig.canvas.draw()
        print("cleared")

    def set_header_label(self,fileheader):
        label_current = Gtk.Builder.get_object(builder, "label_current")
        label_voltage = Gtk.Builder.get_object(builder, "label_voltage")
        label_current.set_text("I = "+si_format(fileheader["setpoint"])+"A")
        label_voltage.set_text("V = "+si_format(fileheader["biasvolt"])+"V")

builder = Gtk.Builder()
builder.add_from_file("main.glade")
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
sw = builder.get_object('scrolledwindow1')

fig = Figure(figsize=(5,4), dpi=100)
ax = fig.add_subplot()
canvas = FigureCanvas(fig)
sw.add(canvas)

window.show_all()
Gtk.main()
