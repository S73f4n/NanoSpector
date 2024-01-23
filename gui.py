#!/usr/bin/env python
import gi
import nanonis_load
from nanonis_load import didv, sxm
import yaml
import os
import io
import re
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

from dataheader import getHeaderLabels

class Handler:
    def __init__(self):
         self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
         self.datastore = []
         self.selectedRows = []

    def on_mainwindow_show(self, *args):
        self.read_settings()
        self.open_folder()
        self.filter_text = ""
        self.filter = yaxisList.filter_new()
        self.filter.set_visible_func(self.filter_function)
        treview = Gtk.Builder.get_object(builder, "yAxisTreeView")
        treview.set_model(self.filter)

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
        selection = Gtk.Builder.get_object(builder, "selection_file")
        selection.handler_block_by_func(self.on_file_selected)
        store.clear()   
        header = Gtk.Builder.get_object(builder, "header_bar")
        header.set_subtitle(settings['file']['path'])
        files = []
        # treeiter = store.append(glob.glob(filepath + "/*.VERT"))
        subDir = settings['file']['path']
        files += [os.path.join(subDir, file) for file in os.listdir(subDir) if os.path.isfile(os.path.join(subDir, file)) and (file.endswith(settings['spec']['extension']) or file.endswith(settings['image']['extension']))]
        for filename in sorted(files, key=os.path.getmtime, reverse=True):
            treeiter = store.append([os.path.basename(filename)])
        selection.handler_unblock_by_func(self.on_file_selected)
    
    def plot_data(self):
        plot_log = Gtk.Builder.get_object(builder, "button_logplot").get_active()
        flatten = Gtk.Builder.get_object(builder, "button_flatten").get_active()
        plane = Gtk.Builder.get_object(builder, "button_plane").get_active()
        index = Gtk.Builder.get_object(builder, "button_index").get_active()
        infobox = Gtk.Builder.get_object(builder, "button_infobox").get_active()
        crop = Gtk.Builder.get_object(builder, "button_crop").get_active()
        ax.cla()
        specdata = []
        handles = None
        try:
            # xaxis = xaxisModel[xaxisIter][0]#
            selected_rows = []
            legendLabels = []
            if len(self.datastore) > 1 and settings['spec']['cmap'] != "default":
                ax.set_prop_cycle('color',[getattr(plt.cm, settings['spec']['cmap'])(i) for i in np.linspace(0, 1, len(self.datastore))])
            for data in self.datastore:
                if isinstance(data,nanonis_load.didv.spectrum) and [sxm for sxm in self.datastore if isinstance(sxm,nanonis_load.sxm.sxm)] == []:
                    if self.selectedRows == []:
                        selected_rows.append(settings['spec']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    yaxislabel = selected_rows[0]
                    if index:
                        if 'index' not in data.data:
                            data.data = data.data.reset_index()
                    else:
                        try:
                            data.data.drop('index', axis=1, inplace=True)
                        except:
                            pass
                    for ch in selected_rows:
                        didv.plot(data, channel=ch, axes=ax,legend=False,logabs=plot_log)
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
                    try:
                        Gtk.Builder.get_object(builder, 'label_comment').set_text("Comment: " + data.header['Comment01'])
                    except KeyError:
                        Gtk.Builder.get_object(builder, 'label_comment').set_text("Comment")
                    self.setHeaderText(data)
                    alpha = 1
                    loc = 'best'
                    if len(self.datastore) > 1:
                        legendLabels.append(os.path.basename(plotname))
                        handles = None
                    elif len(selected_rows) > 1:
                        legendLabels = selected_rows.copy() 
                        handles = None
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header['Saved Date'], fontsize='medium')
                        if infobox:
                            ax.annotate('\n'.join(getHeaderLabels(data)),xy=(0.015,0.8),fontsize='small',xycoords='axes fraction',bbox=dict(alpha=0.7, facecolor='#eeeeee', edgecolor='#bcbcbc', linewidth=0.5,pad=3))
                    else:
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header['Saved Date'], fontsize='medium')
                        legendLabels = getHeaderLabels(data) 
                        handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * len(legendLabels)
                if isinstance(data,nanonis_load.sxm.sxm):
                    if self.selectedRows == []:
                        selected_rows.append(settings['image']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    yaxislabel = selected_rows[0]
                    data.crop_missing_data(channel=selected_rows[0])
                    sxmplot = sxm.plot(data, channel=selected_rows[0],flatten=flatten,subtract_plane=plane,crop_missing=crop,axes=ax)
                    sxmplot.add_spectra([didv for didv in self.datastore if isinstance(didv,nanonis_load.didv.spectrum)],channel=settings['spec']['defaultch'])
                    self.setHeaderText(data)
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
                    legendLabels = getHeaderLabels(data) 
                    handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * len(legendLabels)
                try:
                    if handles == None:
                        ax.legend(legendLabels,loc=loc,fontsize='small',fancybox=True,framealpha=alpha)
                    elif infobox:
                        ax.legend(handles, legendLabels, loc=loc, fontsize='small', fancybox=True, framealpha=alpha, handlelength=0, handletextpad=0)
                except UnboundLocalError:
                    pass
        except KeyError:
            pass
        fig.canvas.draw()


    def setHeaderText(self, data):
        headerString = '\n'.join(key + ": " + str(value) for key, value in data.header.items())
        textView = Gtk.Builder.get_object(builder, 'textViewHeader')
        textViewBuffer = textView.get_buffer()
        textViewBuffer.set_text(headerString)


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

    def on_index_changed(self,button):
        ax.cla()
        self.plot_data()

    def on_button_infobox_toggled(self,button):
        ax.cla()
        self.plot_data()

    def filter_function(self, model, iter, data):
        if self.filter_text == "":
            return True
        else:
            # Get the text to filter
            # Get the text from the model
            item = model[iter][0]
            # Check if the filter text is present in the item
            return self.filter_text.lower() in item.lower()

    def on_filter_text_changed(self, entry):
        self.filter_text = entry.get_text()
        self.filter.refilter()

    def on_filter_text_clear(self, entry, icon, event):
        entry.set_text("")
        self.on_filter_text_changed(entry)
        
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
    
    def cleanIgorName(self, folder):
        folder = folder.replace(folder.split(".")[-1], "")
        folder = folder.replace(".","_").replace("-","").replace("+","p").replace(" ","")
        return folder[:-1]

    def cleanWaveName(self,rows,filename):
        specno = re.search(r'\d+',filename).group()
        units = [re.search(r"\((\w+)\)", wave).group(1) for wave in rows]
        ch = [re.sub(r"\((\w+)\)", '', wave) for wave in rows]
        ch = [wave.replace(".","_").replace("-","").replace("+","p").replace(" ","").replace("[","").replace("]","").replace("(","").replace(")","")+specno for wave in ch]
        return dict(zip(ch, units))

    def export(self,rows,data,filepath):
        os.makedirs(os.path.join(settings['file']['path'],"export"), exist_ok=True)
        filename = os.path.basename(filepath)
        outpath = os.path.join(settings['file']['path'],"export",filename.replace(os.path.splitext(filename)[1],".itx")) 
        igorFolder = self.cleanIgorName(filename)
        waveNames = self.cleanWaveName(rows,igorFolder)
        with open(outpath, 'w') as outfile:
            outfile.write("IGOR\nX NewDataFolder/S "+igorFolder+"\nWAVES/D "+' '.join(waveNames.keys())+ "\nBEGIN\n")
            data.to_csv(outfile,sep="\t",columns=rows,index=False,header=False)
            outfile.write("END\n")
            for wave in waveNames.keys():
                outfile.write("X Setscale d, 0,0, \""+waveNames[wave]+"\", "+wave+"\n")
            outfile.write("X SetDataFolder ::")

    def on_button_export_clicked(self,button):
        try:
            selected_rows = []
            for data in self.datastore:
                if isinstance(data,nanonis_load.didv.spectrum):
                    if self.selectedRows == []:
                        selected_rows.append(settings['spec']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    plotname = data._filename
                    self.export(selected_rows,data.data,plotname)
        except KeyError:
            pass
        
    def on_button_filter_clicked(self,button):
        entry = Gtk.Builder.get_object(builder, "entry_filter_text")
        entry.set_text(button.get_label())
        self.on_filter_text_changed(entry)

    def on_button_header_clicked(self,button):
       headerWindow.show()

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



builder = Gtk.Builder()
builder.add_from_file(os.path.join(os.path.dirname(__file__),"main.glade"))
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
yaxisList = builder.get_object("yaxis_list")
sw = builder.get_object('scrolledwindow1')
swtoolbar = builder.get_object('scrolledwindow2')
headerWindow = builder.get_object('headerWindow')

# fig = Figure(figsize=(4,3), dpi=100)
# ax = fig.add_subplot()
plt.style.use('bmh')
fig, ax = plt.subplots()
# fig.tight_layout()
formatter1 = EngFormatter(sep="\u2009")
canvas = FigureCanvas(fig)
try:
    toolbar = NavigationToolbar(canvas, window)
except TypeError:
    toolbar = NavigationToolbar(canvas)
sw.add(canvas)
swtoolbar.add(toolbar)

#warnings.filterwarnings("error")

window.show_all()
Gtk.main()