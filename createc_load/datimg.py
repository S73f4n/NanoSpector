
import pandas as pd
from .channellist import param30chlist, param32chlist, dacUnits, dat32chlist
import os
import yaml

import re
import zlib
from itertools import compress

import matplotlib
import matplotlib.animation
import matplotlib.pyplot as plt

import numpy as np
from matplotlib import cm

from .utils.misc import XY2D

this_dir = os.path.dirname(__file__)
cgc_file = os.path.join(this_dir, 'Createc_global_const.yaml')
with open(cgc_file, 'rt') as f:
    cgc = yaml.safe_load(f.read())

def dat_header(filename):

        header = {}
        if filename is None:
            return
        with open(filename, "r", errors="ignore") as file_id:
            version = file_id.readline().strip()
            header_lines = 2
            while True:
                file_line = file_id.readline().strip()
                if file_line == "DATA":
                    # self.params = file_id.readline().split()
                    break
                header_lines += 1
                file_line = file_line.split("=")
                if len(file_line) > 1:
                    header[file_line[0]] = file_line[1].strip()
            # self._fix_header()

        return version, header

class DatImg:

    def __init__(self, filename: str):
        self.filename = filename
        self.data = {}
        self.header = dict()

        self._meta_binary, self._data_binary = self._read_binary()

        self.img_array_list = []

        self._bin2meta_dict()
        self._extracted_meta()


        self._read_img()

        # imgs are numpy arrays, with rows with only zeros cropped off
        self.imgs = [self._crop_img(arr) for arr in self.img_array_list]
        # assert(len(set(img.shape for img in self.imgs)) <= 1)
        # Pixels = namedtuple('Pixels', ['y', 'x'])
        self.img_pixels = XY2D(y=self.imgs[0].shape[0],
                               x=self.imgs[0].shape[1])  # size in (y, x)


        for idx, chname in enumerate(self._make_channel_names()):
            self.data[chname] = [
                np.nan_to_num(
                    np.flipud(
                        self.img_array_list[idx].reshape(
                            int(self.x_pixels),int(self.y_pixels)
                            )
                    )
                )
            ]
            self.data[chname].append(
                np.nan_to_num(
                    np.flipud(
                        self.img_array_list[int(idx+self.channels/2)].reshape(
                            int(self.x_pixels),int(self.y_pixels)
                        )
                    )
                )
            )
            

    def _bin2meta_dict(self):
        """
        Convert meta binary to meta info using ansi encoding, filling out the meta dictionary
        Here ansi means Windows-1252 extended ascii code page CP-1252

        Returns
        -------
        None : None
        """

        meta_list = self._meta_binary.decode('cp1252', errors='ignore').split('\n')
        self.header['file_version'] = meta_list[0]
        for line in meta_list:
            temp = line.split('=')
            if len(temp) == 2:
                keywords = temp[0].split(' / ')
                keywords = [kw.strip().lower() for kw in keywords]
                for kw in keywords:
                    self.header[kw] = temp[1][:-1]

    def _extracted_meta(self):
        """
        Assign meta data to easily readable properties.
        One can expand these at will, one may use the method meta_key() to see what keys are available

        Returns
        -------
        None : None
            It just populates all the self.properties
        """
        self.file_version = self.header['file_version']
        self.file_version = ''.join(e for e in self.file_version if e.isalnum())
        self.xPixel = int(self.header['num.x'])
        self.yPixel = int(self.header['num.y'])
        self.channels = int(self.header['channels'])
        self.ch_zoff = float(self.header['chmodezoff'])
        self.ch_bias = float(self.header['chmodebias[mv]'])
        self.chmode = int(self.header['chmode'])
        self.rotation = float(self.header['rotation'])
        self.ddeltaX = int(self.header['dx_div_ddelta-x'])
        self.deltaX_dac = int(self.header['delta x'])
        self.channels_code = self.header['channelselectval']
        self.scan_ymode = int(self.header['scanymode'])
        self.xPiezoConst = float(self.header['xpiezoconst'])
        self.yPiezoConst = float(self.header['ypiezoconst'])
        self.zPiezoConst = float(self.header['zpiezoconst'])
        self.bias = float(self.header['biasvoltage'])
        self.current = float(self.header['fblogiset'])

    def _make_channel_names(self):
        columnnames = []
        channellist = dat32chlist

        for channel in channellist:
            if int(self.channels_code) & channellist[channel] > 0:
                columnnames.append(channel)
        
        return columnnames

    def _read_binary(self):
        with open(self.filename, "rb") as f:
            file_binary = f.read()

        return file_binary[:cgc['g_file_data_bin_offset']], file_binary[cgc['g_file_data_bin_offset']:]

    def _read_img(self):
        """
        Convert img binary to numpy array's, filling out the img_array_list.
        The image was compressed using zlib. So here they are decompressed.
        prerequisite: self.xPixel, self.yPixel, self.channels

        Returns
        -------
        None : None
        """
        try:
            # if it is compressed data, then decompress it
            decompressed_data = zlib.decompress(self._data_binary)
        except zlib.error:
            # else if it is not compressed, then do nothing
            decompressed_data = self._data_binary
        img_array = np.frombuffer(decompressed_data, np.dtype(cgc['g_file_dat_img_pixel_data_npdtype']))
        img_array = np.reshape(img_array[1: self.xPixel * self.yPixel * self.channels + 1],
                               (self.channels * self.yPixel, self.xPixel))
        for i in range(self.channels):
            self.img_array_list.append(img_array[self.yPixel * i:self.yPixel * (i + 1)])

    @staticmethod
    def _crop_img(arr):
        """
        Crop an image, by removing all rows which contain only zeros.

        Parameters
        ----------
        arr : numpy array
            Individual image

        Returns
        -------
        arr : numpy array
            Cropped image
        """
        return arr[~np.all(arr == 0, axis=1)]

    @property
    def offset(self):
        """
        Return offset relatvie to the whole range in angstrom in the format of namedtuple (x, y)

        Returns
        -------
        offset : XY2D
        """
        x_offset = float(self.header['scanrotoffx'])
        y_offset = float(self.header['scanrotoffy'])

        # x_piezo_const = np.float(self.header['xpiezoconst'])
        # y_piezo_const = np.float(self.header['ypiezoconst'])

        x_offset = -x_offset * cgc['g_XY_volt'] * self.xPiezoConst / 2 ** cgc['g_XY_bits']
        y_offset = -y_offset * cgc['g_XY_volt'] * self.yPiezoConst / 2 ** cgc['g_XY_bits']

        # Offset = namedtuple('Offset', ['y', 'x'])
        return XY2D(y=y_offset, x=x_offset)

    @property
    def size(self):
        """
        Return the true size of image in angstrom in namedtuple (x, y)

        Returns
        -------
        size : XY2D
        """
        x = float(self.header['length x[a]']) * self.img_pixels.x / self.xPixel
        y = float(self.header['length y[a]']) * self.img_pixels.y / self.yPixel
        # Size = namedtuple('Size', ['y', 'x'])
        return XY2D(y=y, x=x)

    @property
    def nom_size(self):
        """
        Return the nominal size of image in angstrom in namedtuple (x, y) assuming no pre-termination while scanning.

        Returns
        -------
        nom_size : XY2D
        """
        # Size = namedtuple('Size', ['y', 'x'])
        return XY2D(y=float(self.header['length y[a]']),
                    x=float(self.header['length x[a]']))


    @property
    def x_range(self):
        return float(self.header["length x[a]"])

    @property
    def y_range(self):
        return float(self.header["length y[a]"])

    @property
    def xy_range(self):
        return np.array([self.x_range, self.y_range])

    @property
    def x_pixels(self):
        return float(self.header["num.x"])

    @property
    def y_pixels(self):
        return float(self.header["num.y"])

    @property
    def xy_pixels(self):
        return np.array([self.x_pixels, self.y_pixels])



class Plot:

    def __init__(
        self,
        sxm_data: DatImg,
        channel: str,
        direction: int = 0,
        flatten: bool = False,
        subtract_plane: bool = True,
        crop_missing: bool = False,
        zero: bool = False,
        cover: float = 1,
        cbar: bool = False,
        reverse: bool = False,
        cmap= "gray",
        rasterized=True,
        axes=None
    ):

        self.data = sxm_data

        image_data = np.copy(sxm_data.data[channel][direction])
        avg_dat = image_data[~np.isnan(image_data)].mean()
        image_data[np.isnan(image_data)] = avg_dat
        image_data = np.ma.masked_where(image_data == 0.0, image_data)

        if axes is not None:
            self.ax = axes
            self.fig = self.ax.figure
        else:
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111)
        x_range = sxm_data.x_range
        y_range = sxm_data.y_range
        x_pixels = sxm_data.x_pixels
        y_pixels = sxm_data.y_pixels
        if zero:
            try:
                image_data = image_data - np.min(image_data)
            except:
                pass

        self.image_data = image_data

        if reverse:
            cmap = plt.get_cmap(cmap).reversed()
        else:
            cmap = plt.get_cmap(cmap)
        cmap = plt.get_cmap(cmap)
        cmap.set_bad(color='#dddddd')
        cmap.set_over(color='#ff0000')
        cmap.set_under(color="#0000ff")
        # vmin, vmax = self.central_percentile_limits(cover=cover)
        self.im_plot = self.ax.imshow(
            image_data,
            origin="lower",
            # extent=(0, sxm_data.x_range, 0, sxm_data.y_range),
            cmap=cmap,
            rasterized=rasterized,
            # vmin=vmin,
            # vmax=vmax
        )  # pcolormesh chops off last column and row here
        self.ax.set_aspect("equal")
        if cbar:
            self.fig.colorbar(self.im_plot, ax=self.ax)
