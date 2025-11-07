#!/usr/bin/env python
import gi
import nanonis_load
from nanonis_load import didv, sxm, grid
import yaml
import shutil
import os
import io
import re
import warnings
from datetime import datetime, timezone

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
import matplotlib.cm as cm
from matplotlib import colormaps, style
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar
from matplotlib.ticker import EngFormatter
import matplotlib.patches as mpl_patches

import src.tol_colors as tc

from src.dataheader import getHeaderLabels

class Handler:
    def __init__(self):
        self.settingsDict = {
                            'image': {'extension': 'setImgExt', 'defaultch': 'setImgCh'},
                            'spec': {'extension': 'setSpecExt', 'defaultch': 'setSpecCh', 'defaultchZ': 'setSpecChZ'},
                            }
        self.settingsDropdown = {
                            'general': {'plotstyle': 'setGeneralPlotstyle'},
        }
        self.settingsCmaps = {'image': {'cmap': 'setImgCmap', 'cmapI': 'setImgCmapI', 'cmapdIdV': 'setImgCmapdIdV'}, 'spec': {'cmap': 'setSpecCmap'}, 'fft': {'cmap': 'setFFTCmap'}}
        self.settingsBoxes = {
            'fft': {'window': 'setFFTWindow'},
            'general': {'exportformat': 'setGeneralExportformat'}
            }
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.datastore = []
        self.selectedRows = []
        self.read_settings()
        self.initSettingsWindow()
        self.setPlotstyle()
        self.igorseconds = 2082844800
        self.dateformat = "%d.%m.%Y %H:%M:%S"

    def setPlotstyle(self):
        plt.style.use(settings['general']['plotstyle'])
        plt.rcParams["font.family"] = 'sans-serif'
        plt.rcParams["font.sans-serif"] = ['DejaVu Sans','Arial']
        

    def on_mainwindow_show(self, *args):
        self.open_folder()
        self.filter_text = ""
        self.filter = yaxisList.filter_new()
        self.filter.set_visible_func(self.filter_function)
        treview = Gtk.Builder.get_object(builder, "yAxisTreeView")
        treview.set_model(self.filter)
        self.fileFilter_text = ""
        self.fileFilter = store.filter_new()
        self.fileFilter.set_visible_func(self.fileFilter_function)
        Gtk.Builder.get_object(builder,"file_list_view").set_model(self.fileFilter)

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
        try:
            files += [os.path.join(subDir, file) for file in os.listdir(subDir) if os.path.isfile(os.path.join(subDir, file)) and (file.endswith(settings['spec']['extension']) or file.endswith(settings['image']['extension']) or file.endswith(settings['grid']['extension']))]
            for filename in sorted(files, key=os.path.getmtime, reverse=True):
                treeiter = store.append([os.path.basename(filename)])
        except FileNotFoundError:
            pass
        selection.handler_unblock_by_func(self.on_file_selected)
    
    def replaceLabel(self, label):
        label = label.replace('[AVG] ', '').replace('[bwd] ', '')
        if settings['buttons']['replace']:
            for key, value in settings['label'].items():
                label = label.replace(key, value)
        return label

    def plot_data(self, fft=None):
        for btn in settings['buttons']:
            settings['buttons'][btn] = Gtk.Builder.get_object(builder, "button_"+btn).get_active()
        offsetXslider = Gtk.Builder.get_object(builder, "adjOffset").get_value()
        try:
            self.sxmplot.colorbar.remove()
        except:
            pass
        ax.cla()
        specdata = []
        handles = None
        try:
            # xaxis = xaxisModel[xaxisIter][0]#
            selected_rows = []
            legendLabels = []
            if len(self.datastore) > 1 and settings['spec']['cmap'] != "default":
                    if settings['spec']['cmap'] in settings['csets']:
                        ax.set_prop_cycle('color',[getattr(plt.cm, settings['spec']['cmap'])(i) for i, ch in enumerate(self.datastore)])
                    else:
                        try:
                                ax.set_prop_cycle('color',[getattr(plt.cm, settings['spec']['cmap'])(i) for i in np.linspace(0, 1, len(self.datastore))])
                        except AttributeError:
                            ax.set_prop_cycle('color',list(tc.tol_cset(settings['spec']['cmap'])))
            for countIndex, data in enumerate(self.datastore):
                if isinstance(data,nanonis_load.didv.Spectrum) and [sxm for sxm in self.datastore if isinstance(sxm,nanonis_load.sxm.Sxm)] == []:
                    builder.get_object('sliderLabel').set_text("Y offset")
                    if self.selectedRows == []:
                        if "Z" in data._filename:
                            selected_rows.append(settings['spec']['defaultchZ'])
                        else:
                            selected_rows.append(settings['spec']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    yaxislabel = self.replaceLabel(selected_rows[0])
                    if settings['buttons']['index']:
                        if 'index' not in data.data:
                            data.data = data.data.reset_index()
                    else:
                        try:
                            data.data.drop('index', axis=1, inplace=True)
                        except:
                            pass
                    offsetX = np.mean(self.datastore[0].data[selected_rows[0]]) * offsetXslider*10*len(selected_rows)
                    for ch in selected_rows:
                        if settings['buttons']['average']:
                            bracketPos = ch.find('(')
                            average = ch[:bracketPos] + "[bwd] " + ch[bracketPos:]
                        else:
                            average = None
                        didv.Plot(data, channel=ch, axes=ax,legend=False,average=average,logabs=settings['buttons']['logplot'],multiply=(offsetX*(len(self.datastore)-countIndex)))
                    ax.autoscale(enable=True,axis='both')
                    if settings['buttons']['logplot']:
                        try: 
                            ax.set_yscale('log')
                        except UserWarning:
                            ax.set_yscale('linear')
                    else:
                        ax.set_yscale('linear')
                    ax.set_ylabel(yaxislabel)
                    ax.set_xlabel(self.replaceLabel(ax.get_xlabel()))
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
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)))
                        legendLabels.append(os.path.basename(plotname))
                        handles = None
                    elif len(selected_rows) > 1:
                        legendLabels = selected_rows.copy() 
                        handles = None
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header['Saved Date'], fontsize='medium')
                        if settings['buttons']['infobox']:
                            ax.annotate('\n'.join(getHeaderLabels(data)),xy=(0.015,0.8),fontsize='small',xycoords='axes fraction',bbox=dict(alpha=0.7, facecolor='#eeeeee', edgecolor='#bcbcbc', linewidth=0.5,pad=3))
                    else:
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header['Saved Date'], fontsize='medium')
                        legendLabels = getHeaderLabels(data) 
                        handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * len(legendLabels)
                if isinstance(data,nanonis_load.sxm.Sxm):
                    builder.get_object('sliderLabel').set_text("Contrast")
                    if self.selectedRows == []:
                        selected_rows.append(settings['image']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    data.crop_missing_data(channel=selected_rows[0])
                    if "Current" in selected_rows[0]:
                        cmap = settings['image']['cmapI']
                    elif "LI" in selected_rows[0]: 
                        cmap = settings['image']['cmapdIdV']
                    else:
                        cmap = settings['image']['cmap']
                    if "(m)" in selected_rows[0]:
                        fixzero = True
                    else: 
                        fixzero = False
                    alpha = 0.4
                    loc = 'lower right'
                    plotname = data.filename
                    if cmap == 'default':
                        self.sxmplot = sxm.Plot(data, channel=selected_rows[0],flatten=settings['buttons']['flatten'],subtract_plane=settings['buttons']['plane'],zero=fixzero,cover=1.0-offsetXslider,axes=ax)
                    else:
                        try:
                            self.sxmplot = sxm.Plot(data, channel=selected_rows[0],cmap=cmap,flatten=settings['buttons']['flatten'],subtract_plane=settings['buttons']['plane'],zero=fixzero,cover=1.0-offsetXslider,axes=ax)
                        except ValueError:
                            self.sxmplot = sxm.Plot(data, channel=selected_rows[0],flatten=settings['buttons']['flatten'],subtract_plane=settings['buttons']['plane'],zero=fixzero,cover=1.0-offsetXslider,axes=ax)
                    if fft: 
                        self.sxmplot.fft(windowFilter=settings['fft']['window'],level=settings['fft']['level'])
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + " (FFT) \n" + data.header[':REC_DATE:'][0] + " " +  data.header[':REC_TIME:'][0], fontsize='small')
                    else:
                        didvData = [didv for didv in self.datastore if isinstance(didv,nanonis_load.didv.Spectrum)]
                        didvLabel = [re.findall(r"\d+", didv._filename)[-1].lstrip('0') for didv in didvData] 
                        self.sxmplot.add_spectra(didvData,labels=didvLabel,channel=settings['spec']['defaultch'])
                        fig.axes[0].set_title(os.path.basename(os.path.dirname(plotname)) + "/" + os.path.basename(plotname) + "\n" + data.header[':REC_DATE:'][0] + " " +  data.header[':REC_TIME:'][0] + '\n{:g} × {:g} nm'.format(data.x_range,data.y_range),
                                    fontsize='small')
                        fig.axes[0].axis('off')            
                    self.setHeaderText(data)
                    # try:
                    #     self.sxmplot.colorbar.ax.yaxis.set_major_formatter(formatter1)
                    # except:
                    #     pass
                    # fig.delaxes(fig.axes[1])
                    # fig.axes[1].remove()
                    # fig.set_figwidth(8)
                    legendLabels = getHeaderLabels(data) 
                    handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * len(legendLabels)
                if isinstance(data,nanonis_load.grid.Grid):
                    if self.selectedRows == []:
                        selected_rows.append(settings['image']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    
                    builder.get_object('sliderLabel').set_text("Energy")
                    self.gridplot = data.plot(channel=selected_rows[0],axes=ax)
                try:
                    if handles == None and settings['buttons']['legend']:
                        ax.legend(legendLabels,loc=loc,fontsize='small',fancybox=True,framealpha=alpha)
                    elif handles is not None and settings['buttons']['infobox']:
                        ax.legend(handles, legendLabels, loc=loc, fontsize='small', fancybox=True, framealpha=alpha, handlelength=0, handletextpad=0)
                except UnboundLocalError:
                    pass
        except KeyError:
            pass
        fig.canvas.draw()
        fig.canvas.mpl_connect("button_press_event", self.on_fig_click)


    def setHeaderText(self, data):
        headerString = '\n'.join(key + ": " + str(value) for key, value in data.header.items())
        textView = Gtk.Builder.get_object(builder, 'textViewHeader')
        textViewBuffer = textView.get_buffer()
        textViewBuffer.set_text(headerString)


    def getDataFromFiles(self, files):
        self.datastore = []
        for thisFile in files:
            filename = os.path.join(settings['file']['path'],thisFile)
            if filename.endswith(settings['spec']['extension']):
                self.datastore.append(didv.Spectrum(filename))
            elif filename.endswith(settings['image']['extension']):
                self.datastore.append(sxm.Sxm(filename))
            elif filename.endswith(settings['grid']['extension']):
                self.datastore.append(grid.Grid(filename))
            else:
                return 0
            self.setChannelList(self.datastore[-1].data.keys())

    def on_selection_yaxis_changed(self,selection):
        yaxisModel, yaxisIter = selection.get_selected_rows()
        if yaxisIter:
            # try:
            #     self.sxmplot.colorbar.remove()
            # except:
            #     pass
            ax.cla()
            specAx.cla()
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
    
    def on_fig_click(self,event):
        if isinstance(self.datastore[0],nanonis_load.grid.Grid):
            gData = self.datastore[0]
            specAx.cla()
            gData.click = (event.xdata, event.ydata)
            if self.selectedRows == []:
                isPlot = gData.show_spectra(channel=settings['grid']['defaultch'],ax=specAx)
                yaxislabel = self.replaceLabel(settings['grid']['defaultch'])
            else:
                isPlot = gData.show_spectra(channel=self.selectedRows[0],ax=specAx)
                yaxislabel = self.replaceLabel(self.selectedRows[0])

            if isPlot is not None:
                specAx.set_ylabel(yaxislabel)
                specAx.set_xlabel(self.replaceLabel(gData.header["Sweep Signal"].strip('"')))
                specAx.xaxis.set_major_formatter(formatter1)
                specAx.yaxis.set_major_formatter(formatter1)
                specFig.canvas.draw()
                # specFig.tight_layout()
                fig.canvas.draw()
                specWindow.show_all()
                if not specWindow.is_visible():
                    specWindow.present()
        
    
    def on_button_fft_clicked(self, button):
        # try:
        #     self.sxmplot.colorbar.remove()
        # except:
        #     pass
        ax.cla()
        self.plot_data(fft=True)

    def on_logplot_changed(self,button):
        # try:
        #     self.sxmplot.colorbar.remove()
        # except:
        #     pass
        ax.cla()
        self.plot_data()
    
    def on_slider_changed(self,button):
        if isinstance(self.datastore[0],nanonis_load.grid.Grid):
            self.datastore[0].update_bias(button.get_value())
        else: 
            ax.cla()
            self.plot_data()


        

    def on_index_changed(self,button):
        # try:
        #     self.sxmplot.colorbar.remove()
        # except:
        #     pass
        ax.cla()
        self.plot_data()

    def on_button_infobox_toggled(self,button):
        # try:
        #     self.sxmplot.colorbar.remove()
        # except:
        #     pass
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
    
    def fileFilter_function(self, model, iter, data):
        if self.fileFilter_text == "":
            return True
        else:
            # Get the text to filter
            # Get the text from the model
            item = model[iter][0]
            # Check if the filter text is present in the item
            return self.fileFilter_text.lower() in item.lower()

    def on_filter_text_changed(self, entry):
        self.filter_text = entry.get_text()
        self.filter.refilter()

    def on_filter_text_clear(self, entry, icon, event):
        entry.set_text("")
        self.on_filter_text_changed(entry)

    def on_filter_file_changed(self, entry):
        selection = Gtk.Builder.get_object(builder, "selection_file")
        self.fileFilter_text = entry.get_text()
        selection.handler_block_by_func(self.on_file_selected)
        self.fileFilter.refilter()
        selection.handler_unblock_by_func(self.on_file_selected)

    def on_filter_file_clear(self, entry, icon, event):
        entry.set_text("")
        self.on_filter_file_changed(entry)
        
    def read_settings(self):
        global settings
        with open(os.path.join(os.path.dirname(__file__),"settings_example.yaml"), "r") as exampleFile:
            exampleSettings = yaml.safe_load(exampleFile)   
        if os.path.exists(os.path.join(os.path.dirname(__file__),"settings.yaml")):
            with open(os.path.join(os.path.dirname(__file__),"settings.yaml"), "r") as settingsFile:
                FileSettings = yaml.safe_load(settingsFile)  
            settings = exampleSettings | FileSettings
            for data in settings.keys():
                if type(settings[data]) == dict:
                    settings[data] = exampleSettings[data] | FileSettings[data]
        else:
            settings = exampleSettings
    
    def write_settings(self):
        for btn in settings['buttons']:
            settings['buttons'][btn] = Gtk.Builder.get_object(builder, "button_"+btn).get_active()
        with open(os.path.join(os.path.dirname(__file__), "settings.yaml"), 'w') as file:
            yaml.dump(settings, file)

    def on_button_clear_clicked(self, button):
        ax.cla()
        fig.canvas.draw()
    
    def on_button_reverse_clicked(self, button):
        try:
            if self.datastore is not None and len(self.datastore) > 1:
                self.datastore.reverse()
        except:
            pass
        try:
            if self.selectedRows is not None and len(self.selectedRows) > 1:
             self.selectedRows.reverse()
        except:
            pass

        self.on_logplot_changed(button)
    
    def cleanIgorName(self, folder):
        folder = folder.replace(folder.split(".")[-1], "")
        folder = folder.replace(".","_").replace("-","").replace("+","p").replace(" ","")
        return folder[:-1]

    def cleanWaveName(self,rows,filename):
        try:
            specno = re.search(r'\d+',filename).group()
        except AttributeError:
            specno = ""
        units = [re.search(r"\((\w+)\)", wave).group(1) for wave in rows]
        ch = [re.sub(r"\((\w+)\)", '', wave) for wave in rows]
        ch = [wave.replace(".","_").replace("-","").replace("+","p").replace(" ","").replace("[","").replace("]","").replace("(","").replace(")","")+specno for wave in ch]
        return dict(zip(ch, units))

    def export(self,rows,data,filepath):
        os.makedirs(os.path.join(settings['file']['path'],"export"), exist_ok=True)
        filename = os.path.basename(filepath)
        if settings['general']['exportformat'] == "IgorPro":
            outpath = os.path.join(settings['file']['path'],"export",filename.replace(os.path.splitext(filename)[1],".itx")) 
            igorFolder = self.cleanIgorName(filename)
            waveNames = self.cleanWaveName(rows,igorFolder)
            with open(outpath, 'w') as outfile:
                outfile.write("IGOR\nX NewDataFolder/S "+igorFolder+"\nWAVES/D "+' '.join(waveNames.keys())+ "\nBEGIN\n")
                data.data.to_csv(outfile,sep="\t",columns=rows,index=False,header=False)
                outfile.write("END\n")
                for wave in waveNames.keys():
                    outfile.write("X Setscale d, 0,0, \""+waveNames[wave]+"\", "+wave+"\n")
                try:
                    saveddate = datetime.strptime(data.header['Saved Date'], self.dateformat)
                    outfile.write("X Variable saveddate = "+str(saveddate.replace(tzinfo=timezone.utc).timestamp()+self.igorseconds)+"\n")
                    outfile.write("X Note "+wave+" \"Saved Date: "+data.header['Saved Date'] +"\\n"+'\\n'.join(self.cleanHeader(data))+"\"\n")
                except (TypeError, ValueError):
                    pass
                outfile.write("X SetDataFolder ::")
        elif settings['general']['exportformat'] == "ASCII":
            outpath = os.path.join(settings['file']['path'],"export",filename.replace(os.path.splitext(filename)[1],".csv")) 
            with open(outpath, 'w') as outfile:
                data.data.to_csv(outfile,sep="\t",columns=rows,index=False,header=True)
    
    def exportsxm(self,rows,data,filepath):
        os.makedirs(os.path.join(settings['file']['path'],"export"), exist_ok=True)
        filename = os.path.basename(filepath)
        
        # Apply flatten and plane to export data
        if settings["buttons"]["flatten"]:
            exportdata = signal.detrend(data.get_data(rows[0]))
        elif settings["buttons"]["plane"]:
            exportdata = sxm.subtract_plane(data.get_data(rows[0]))
        else:
            exportdata = data.get_data(rows[0])
        
        if settings['general']['exportformat'] == "IgorPro":
            outpath = os.path.join(settings['file']['path'],"export",filename.replace(os.path.splitext(filename)[1],".itx")) 
            igorFile = self.cleanIgorName(filename)
            unit = re.search(r"\((\w+)\)", rows[0]).group(1)
            with open(outpath, "w") as outfile:
                outfile.write("IGOR\nWAVES/D/N=("+str(data.x_pixels)+","+str(data.y_pixels)+") "+igorFile+ "\nBEGIN\n")
                np.savetxt(outfile, np.transpose(exportdata), delimiter="\t")
                outfile.write("END\n")
                outfile.write("X Setscale d, 0,0, \""+unit+"\", "+igorFile+"\n")
                outfile.write("X Setscale/I x, 0,"+str(data.x_range)+", \"m\", "+igorFile+"\n")
                outfile.write("X Setscale/I y, 0,"+str(data.y_range)+", \"m\", "+igorFile+"\n")
                outfile.write("X Note "+igorFile+" \"Saved Date: "+data.header[':REC_DATE:'][0] + " " +  data.header[':REC_TIME:'][0] +"\\n"+'\\n'.join(self.cleanHeader(data))+"\"\n")

        elif settings['general']['exportformat'] == "ASCII":
            outpath = os.path.join(settings['file']['path'],"export",filename.replace(os.path.splitext(filename)[1],".csv")) 
            np.savetxt(outpath, exportdata, delimiter=",")

    def exportgrid(self,rows,data,filepath):
        filename = os.path.basename(filepath)
        basename = os.path.splitext(filename)[0]
        os.makedirs(os.path.join(settings['file']['path'],"export",basename), exist_ok=True)
        igorFolder = self.cleanIgorName(filename)
        waveNames = self.cleanWaveName(rows,igorFolder)
        if settings['general']['exportformat'] == "IgorPro":
            exportfile = os.path.join(settings['file']['path'],"export",basename+".itx")
            for i, wave in enumerate(waveNames.keys()):
                unit = re.search(r"\((\w+)\)", rows[i]).group(1)
                flat_data = data.data[rows[i]].flatten(order="F")
                with open(exportfile, "w") as outfile:
                    outfile.write("IGOR\n")
                    outfile.write(f"WAVES/N=({data.y_pixels:g},{data.x_pixels:g},{len(data.biases):g}) {wave}\n")
                    outfile.write("BEGIN\n")
                    for i, val in enumerate(flat_data):
                        outfile.write(f"{val:.6e} ")
                        if (i + 1) % 10 == 0:
                            outfile.write("\n")
                    outfile.write("\nEND\n")
                    outfile.write(f"X Setscale/I x, 0, {data.x_size*1e-9:.6g}, \"m\", {wave}\n")
                    outfile.write(f"X Setscale/I y, 0, {data.y_size*1e-9:.6g}, \"m\", {wave}\n")
                    outfile.write(f"X Setscale/I z, {data.biases[0]:.6g},{data.biases[-1]:.6g}, \"V\", {wave}\n")
                    outfile.write(f"X Setscale d, 0,0, \"{unit}\", {wave}\n")
        if settings['general']['exportformat'] == "ASCII":
            exportfile = os.path.join(settings['file']['path'],"export",basename+".dat")
            for i, wave in enumerate(waveNames.keys()):
                reshaped_data = data.data[rows[i]].reshape(-1, data.data[rows[i]].shape[2]).T
                np.savetxt(exportfile, reshaped_data, delimiter=",")

    def cleanHeader(self,headerData):
        return [x.replace("$","").replace("{","").replace("}","") for x in getHeaderLabels(headerData)]

    def initSettingsWindow(self):
        plotstyleGtk = Gtk.Builder.get_object(builder, "setGeneralPlotstyle")
        for ps in style.available:
            plotstyleGtk.append_text(ps)
        plotstyleGtk.set_active(style.available.index(settings['general']['plotstyle'])) 
        for setType, setting in self.settingsBoxes.items():
            for setName, gtkName in setting.items():
                for window in settings[setType][setName+'s']:
                    Gtk.Builder.get_object(builder, gtkName).append_text(window)
        for color in settings['cmaps']:
            for boxes in self.settingsCmaps.values():
                for box in boxes.values():
                    Gtk.Builder.get_object(builder, box).append_text(color)
        for setType, setting in self.settingsBoxes.items():
            for setName, gtkName in setting.items():
                Gtk.Builder.get_object(builder, gtkName).set_active(settings[setType][setName+'s'].index(settings[setType][setName]))
        for setType, setting in self.settingsCmaps.items():
            for setName, gtkName in setting.items():
                Gtk.Builder.get_object(builder, gtkName).set_active(settings['cmaps'].index(settings[setType][setName]))
        for setType, setting in self.settingsDict.items():
            for setName, gtkName in setting.items():
                Gtk.Builder.get_object(builder, gtkName).set_text(settings[setType][setName])
        Gtk.Builder.get_object(builder, 'adjFFTLevel').set_value(settings['fft']['level'])
        for btn, value in settings['buttons'].items():
            Gtk.Builder.get_object(builder, "button_"+btn).set_active(value)
        labelstore.clear()
        for lb in settings['label'].items():
            model = labelstore.append(lb)
        labelstore.append(["Add channel...",""])

    def readSettingsfromWindow(self):
        for setType, setting in self.settingsDict.items():
            for setName, gtkName in setting.items():
                targetValue = Gtk.Builder.get_object(builder, gtkName).get_text()
                if targetValue is not None:
                    settings[setType][setName] = targetValue
        for setType, setting in self.settingsCmaps.items():
            for setName, gtkName in setting.items():
                targetValue = Gtk.Builder.get_object(builder, gtkName).get_active_text()
                if targetValue is not None:
                    settings[setType][setName] = targetValue
        for setType, setting in self.settingsDropdown.items():
            for setName, gtkName in setting.items():
                targetValue = Gtk.Builder.get_object(builder, gtkName).get_active_text()
                if targetValue is not None:
                    settings[setType][setName] = targetValue
        for setType, setting in self.settingsBoxes.items():
            for setName, gtkName in setting.items():
                targetValue = Gtk.Builder.get_object(builder, gtkName).get_active_text()
                if targetValue is not None:
                    settings[setType][setName] = targetValue
        settings['fft']['level'] = Gtk.Builder.get_object(builder, 'adjFFTLevel').get_value()
        self.setPlotstyle()
        settings['label'] = {row[0]: row[1] for row in labelstore}
        del settings['label']['Add channel...']

    def on_button_export_clicked(self,button):
        try:
            selected_rows = []
            for data in self.datastore:
                if isinstance(data,nanonis_load.didv.Spectrum):
                    if self.selectedRows == []:
                        selected_rows.append(settings['spec']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    plotname = data._filename
                    self.export(selected_rows,data,plotname)
                elif isinstance(data,nanonis_load.sxm.Sxm):
                    if self.selectedRows == []:
                        selected_rows.append(settings['image']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    plotname = data.filename
                    self.exportsxm(selected_rows,data,plotname)
                elif isinstance(data, nanonis_load.grid.Grid):
                    if self.selectedRows == []:
                        selected_rows.append(settings['grid']['defaultch'])
                    else:
                        selected_rows = self.selectedRows
                    plotname = data.filename
                    self.exportgrid(selected_rows,data,plotname)
        except KeyError:
            pass
        
    def on_button_filter_clicked(self,button):
        entry = Gtk.Builder.get_object(builder, "entry_filter_text")
        entry.set_text(button.get_label())
        self.on_filter_text_changed(entry)

    def on_button_header_clicked(self,button):
       headerWindow.show()
       headerWindow.present()
    
    def on_headerWindow_destroy(self, *data):
        headerWindow.hide()
        return True

    def on_specWindow_destroy(self, *data):
        specWindow.hide()
        return True

    def on_buttonSettings_clicked(self,button):
        # self.writeSettingstoWindow()
        response = settingsDialog.run()
        if response == Gtk.ResponseType.APPLY:
            self.readSettingsfromWindow()
        else:
            labelstore.clear()
            for lb in settings['label'].items():
                model = labelstore.append(lb)
            labelstore.append(["Add channel...",""])
        settingsDialog.hide()
        self.write_settings()
        self.plot_data()

    def on_button_savefig_clicked(self,button):
        filemodel, fileiter = Gtk.Builder.get_object(builder, "selection_file").get_selected_rows()
        savefig = io.BytesIO()
        os.makedirs(os.path.join(settings['file']['path'],"export"), exist_ok=True)
        if fileiter:
            savefig.name = os.path.join(settings['file']['path'], "export", "export.png")
            selectedFiles = [filemodel[path][0] for path in fileiter] 
            if len(selectedFiles) > 1:
                selectedNums = [re.findall(r"\d+", filename)[-1] for filename in selectedFiles]
                exportFile = selectedFiles[-1].replace(os.path.splitext(selectedFiles[-1])[1],"-"+str(selectedNums[0])+".png") 
            else:
                exportFile = selectedFiles[0].replace(os.path.splitext(selectedFiles[0])[1],".png")
            savefig.name = os.path.join(settings['file']['path'], "export", exportFile)
            fig.savefig(savefig.name, dpi=300,format='png',bbox_inches='tight')
            savefig.seek(0)
            piximage = Gtk.Image.new_from_file(savefig.name)
            self.clipboard.set_image(piximage.get_pixbuf())
            fig.canvas.draw()
    
    def on_label_data_edited(self, widget, path, new_text):
        labelstore[path][0] = new_text
        if new_text == "":
            del labelstore[path]
        elif int(path) == len(labelstore) - 1:
            labelstore.append(["Add channel...",""])

    def on_label_friendly_edited(self, widget, path, new_text):
        labelstore[path][1] = new_text
        if new_text == "":
            del labelstore[path]
        elif int(path) == len(labelstore) - 1:
            labelstore.append(["Add channel...",""])
    
    def on_labelTreeView_key_press_event(self, widget, event):
        if event.keyval == Gdk.KEY_Delete:  # Check if "Delete" key was pressed
                model, tree_iter = Gtk.Builder.get_object(builder, "selection_label").get_selected()
                if tree_iter is not None:
                    path = model.get_path(tree_iter)
                    if path[0] != len(model) - 1:  # Prevent deleting the last "Add Row"
                        model.remove(tree_iter)  # Remove the selected row



builder = Gtk.Builder()
builder.add_from_file(os.path.join(os.path.dirname(__file__),"src/main.glade"))
labelstore = builder.get_object("label_list")
builder.connect_signals(Handler())

window = builder.get_object("mainwindow")
store=builder.get_object('file_list')
yaxisList = builder.get_object("yaxis_list")
specWindow = builder.get_object('specWindow')
sw = builder.get_object('scrolledwindow1')
specsw = builder.get_object('specScrolledWindow1')
swtoolbar = builder.get_object('scrolledwindow2')
specswtoolbar = builder.get_object('specScrolledWindow2')
headerWindow = builder.get_object('headerWindow')
settingsDialog = builder.get_object('settingsDialog')

# fig = Figure(figsize=(4,3), dpi=100)
# ax = fig.add_subplot()
fig, ax = plt.subplots(layout="constrained")
specFig, specAx = plt.subplots(layout="constrained")
# fig.tight_layout()
formatter1 = EngFormatter(sep="\u2009")
canvas = FigureCanvas(fig)
specCanvas = FigureCanvas(specFig)

try:
    toolbar = NavigationToolbar(canvas, window)
except TypeError:
    toolbar = NavigationToolbar(canvas)

try:
    specToolbar = NavigationToolbar(specCanvas, specWindow)
except:
    specToolbar = NavigationToolbar(specCanvas)

sw.add(canvas)
swtoolbar.add(toolbar)

specsw.add(specCanvas)
specswtoolbar.add(specToolbar)

#warnings.filterwarnings("error")

window.show_all()
Gtk.main()