from nanonis_load import grid
import matplotlib.pyplot as plt

filename = "/home/stefan/mKSTM_Data/2023-08-18/GridSpectroscopy002.3ds"
specgrid = grid.nanonis_3ds(filename)
gridplot = grid.plot(specgrid,channel='LI Demod X (A)')
gridplot.colormap('viridis')
plt.show()
