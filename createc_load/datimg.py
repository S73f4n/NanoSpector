
import pandas as pd
from .channellist import param30chlist, param32chlist, dacUnits, dat32chlist
from .channellist import createcConstants as cgc
import os
import yaml

import scipy.signal

import re
import zlib
from itertools import compress

import matplotlib
import matplotlib.animation
import matplotlib.pyplot as plt

import numpy as np
from matplotlib import cm

from .utils.misc import XY2D



class DatImg:

    def __init__(self, filename: str):
        self.filename = filename
        self.data = {}
        self.header = dict()
        self.y_mask = None

        self._meta_binary, self._data_binary = self._read_binary()

        self.img_array_list = []

        self._bin2meta_dict()
        self._extracted_meta()


        self._read_img()

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

        return file_binary[:cgc['data_bin_offset']], file_binary[cgc['data_bin_offset']:]

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
        img_array = np.frombuffer(decompressed_data, np.dtype(cgc['dat_img_pixel_data_npdtype']))
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


    def crop_missing_data(self, channel: str, direction: int = 0):
        r"""
        Sets self.y_mask to exclude missing data in the y-direction.
        """
        channel_data = self.data[channel][direction % 2]
        if self.y_mask is None:
            self.y_mask = ~(channel_data == 0.0).any(axis=1)
        else:
            self.y_mask = self.y_mask & (~(channel_data == 0.0).any(axis=1))

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


    def subtract_plane(self, channel: str, direction: int = 0) -> np.ndarray:
        """
        Returns the specified channel and direction of the data with a plane subtracted.
        """
        return subtract_plane(self.data[channel][direction])


def subtract_plane(data: np.ndarray) -> np.ndarray:
    """
    Returns the input but with a plane subtracted from the entire array.
    The input MUST be a 2D array.

    Parameters
    ----------
    data : np.ndarray
        2D numpy array containing data.

    Returns
    -------
    output : ndarray
        The data with a fitted 2D plane subtracted from it.
    """

    if len(data.shape) != 2:
        raise ValueError("Error: input array is not 2-dimensional.")

    data = np.ma.masked_where(data == 0, data)
    try:
        data = np.ma.getdata(data[~data.mask.any(axis=1)])
    except:
        data = np.ma.getdata(data)

    x_dim = data.shape[1]
    y_dim = data.shape[0]

    X, Y = np.meshgrid(np.arange(0, x_dim), np.arange(0, y_dim))
    flattened_X = X.flatten()
    flattened_Y = Y.flatten()
    flattened_data = data.flatten()

    A = np.c_[
        flattened_X, flattened_Y, np.ones(len(flattened_X))
    ]  # Puts flattened_X, flattened_Y, and a column of ones into the columns of a matrix A
    C, _, _, _ = scipy.linalg.lstsq(
        A, flattened_data
    )  # Finds the least squares solution to Ax = flattened_data where x contains the coefficients of the plane equation

    Z = C[0] * X + C[1] * Y + C[2]  # Feeds X and Y into the fitted plane equation

    return data - Z


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
        cmap = "gray",
        overrange: bool = False,
        rasterized=True,
        axes=None
    ):

        self.data = sxm_data

        image_data = np.copy(sxm_data.data[channel][direction])
        avg_dat = image_data[~np.isnan(image_data)].mean()
        image_data[np.isnan(image_data)] = avg_dat
        image_data = np.ma.masked_where(image_data == 0.0, image_data)
        if (flatten == True) and (subtract_plane == False):
            image_data[self.data.y_mask]=scipy.signal.detrend(image_data[self.data.y_mask])

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


        if subtract_plane == True:
            image_data[self.data.y_mask] = sxm_data.subtract_plane(channel, direction)
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
        if overrange == True:
            cmap.set_over(color='#ff0000')
            cmap.set_under(color="#0000ff")
        vmin, vmax = self.central_percentile_limits(cover=cover)
        self.im_plot = self.ax.imshow(
            image_data,
            origin="lower",
            # extent=(0, sxm_data.x_range, 0, sxm_data.y_range),
            cmap=cmap,
            rasterized=rasterized,
            vmin=vmin,
            vmax=vmax
        )  # pcolormesh chops off last column and row here
        self.ax.set_aspect("equal")
        if cbar:
            self.fig.colorbar(self.im_plot, ax=self.ax)


    def central_percentile_limits(self, cover=1.0, *, ignore_nan=True, mask=None, eps=1e-15):
        """
        Return (vmin, vmax) capturing the central `cover` fraction of values in `a`.

        Parameters
        ----------
        a : array-like
            Image / matrix values.
        cover : float in (0, 1]
            Fraction of the histogram to keep. Example: 0.98 keeps the central 98%
            (clips 1% on each tail). 1.0 means no clipping.
        ignore_nan : bool
            If True, ignore NaNs when computing percentiles.
        mask : array-like of bool, optional
            If provided, only use values where mask is True.
        eps : float
            Tiny expansion added if vmin == vmax to avoid zero range.

        Returns
        -------
        (vmin, vmax) : tuple of floats
        """
        a = np.asanyarray(self.image_data)

        if mask is not None:
            a = a[mask]

        # Flatten and filter finite values
        a = a.ravel()
        if ignore_nan:
            a = a[np.isfinite(a)]

        if a.size == 0:
            raise ValueError("No finite data to compute percentile limits.")

        low_q = (1 - cover) * 50.0
        high_q = 100.0 - low_q

        # Percentiles are unitless—works regardless of the data's physical units.
        pfunc = np.nanpercentile if ignore_nan else np.percentile
        vmin, vmax = pfunc(a, [low_q, high_q])

        if not np.isfinite(vmin): vmin = np.min(a)
        if not np.isfinite(vmax): vmax = np.max(a)
        if vmin == vmax:
            vmin -= eps
            vmax += eps

        return float(vmin), float(vmax)