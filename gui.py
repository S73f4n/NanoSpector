import gi
import glob

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class Handler:
    def on_mainwindow_destroy(self, *args):
        Gtk.main_quit()

    def on_button1_clicked(self, button):
        print("Hello World!")
    
    def on_current_folder_changed(self, folder_chooser):
        print("Folder:" + folder_chooser.get_filename())

    def on_selection_changed(self, folder_chooser):
        print("Folder:" + folder_chooser.get_filename())
        # treeiter = store.append(glob.glob(folder_chooser.get_filename() + "/*.VERT"))
        for filename in glob.glob(folder_chooser.get_filename() + "/*.VERT"):
            print(filename)
            treeiter = store.append([filename.split("/")[-1]])


builder = Gtk.Builder()
builder.add_from_file("main.glade")
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
window.show_all()

Gtk.main()
