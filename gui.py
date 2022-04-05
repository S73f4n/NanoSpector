import gi
import glob

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


from matplotlib.figure import Figure
from numpy import arange, pi, random, linspace
import matplotlib.cm as cm
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

class Handler:
    def on_mainwindow_destroy(self, *args):
        Gtk.main_quit()

    def on_button1_clicked(self, button):
        print("Hello World!")
    
    def on_current_folder_changed(self, folder_chooser):
        print("Folder:" + folder_chooser.get_filename())

    def on_selection_changed(self, folder_chooser):
        print("Folder:" + folder_chooser.get_filename())
        header = Gtk.Builder.get_object(builder, "header_bar")
        header.set_subtitle(folder_chooser.get_filename())
        # treeiter = store.append(glob.glob(folder_chooser.get_filename() + "/*.VERT"))
        for filename in glob.glob(folder_chooser.get_filename() + "/*.VERT"):
            treeiter = store.append([filename.split("/")[-1]])

    def on_file_selected(self, selection):
        model, treeiter = selection.get_selected_rows()
        if treeiter is not None:
            print("You selected", model[treeiter][0])

builder = Gtk.Builder()
builder.add_from_file("main.glade")
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
sw = builder.get_object('scrolledwindow1')

fig = Figure(figsize=(5,5), dpi=100)
ax = fig.add_subplot(111, projection='polar')

N = 20
theta = linspace(0.0, 2 * pi, N, endpoint=False)
radii = 10 * random.rand(N)
width = pi / 4 * random.rand(N)

bars = ax.bar(theta, radii, width=width, bottom=0.0)

for r, bar in zip(radii, bars):
    bar.set_facecolor(cm.jet(r / 10.))
    bar.set_alpha(0.5)

ax.plot()

canvas = FigureCanvas(fig)
sw.add_with_viewport(canvas)
window.show_all()

Gtk.main()
