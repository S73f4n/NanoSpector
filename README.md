# Nanonis Viewer

Welcome to Nanonis Viewer a small program that allows you to quickly view images and spectra saved by Specs Nanonis software. Nanonis Viewer works best if you save your files in one directory, that you can select to browse all viewable files. 

## Screenshots
 
Screenshots to be added

## Installation

### Windows binaries

For windows users, an executable binary version is available on the release page. Just download the whole folder and run NanonisViewer.exe.

### Conda

If you are using a conda python environment you can install the necessary dependencies by
```
conda install scipy pyaml pandas gtk3 matplotlib pygobject adwaita-icon-theme
```
You can then run the gui.py from within that environment.

## Usage
Usage of Nanonis Viwer is rather intuitive. Select the folder you data files are in and click on a specific file to view it. If the default channel is present in that file it will already be plotted. Otherwise select the respective channel from the list. Selecting multiple files as well as channels is also possible.
Basic image analysis is available in the main window. Flatten, plane level or crop the images or calculate the 2D FFT.
The save button save a .png image in the export subfolder of your working directory and copies it to the clip board automatically

## Settings
The file extensions Nanonis Viewer is looking for, the default channels and colourmaps can be changed from the settings window. FFT settings alow you to change the window function that is applied to the image before calculating the FFT as well as the cut off level of the finial FFT plot.

## Support
Bug reports are sent to st.schulte@fz-juelich.de
