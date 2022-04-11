from __future__ import annotations # For TYPE_CHECKING

from abc import ABC, abstractmethod
import xarray as xr
import numpy as np
from copy import copy
import pandas as pd
from typing import List
import sys
import re

# Import objects
from ..grd.grd_mod import Grid

# Import abstract classes and needed instances of them
from .process import BoundaryProcessor, Multiply
from .pick import PointPicker, TrivialPicker
from .read import BoundaryReader
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .write import BoundaryWriter # Abstract class

# Import default values and auxiliry functions
from .. import msg
from ..aux import day_list


class Boundary:
    def __init__(self, grid: Grid, name: str="AnonymousBoundary"):
        self.grid = copy(grid)
        self._name = copy(name)
        self._convention = None
        self._history = []
        return

    def import_boundary(self, start_time: str, end_time: str, boundary_reader: BoundaryReader,  point_picker: PointPicker = TrivialPicker()):
        """Imports boundary spectra from a certain source.

        Spectra are import between start_time and end_time from the source
        defined in the boundary_reader. Which spectra to choose spatically
        are determined by the point_picker.
        """

        self._history.append(copy(boundary_reader))

        msg.header(boundary_reader, "Reading coordinates of spectra...")
        lon_all, lat_all = boundary_reader.get_coordinates(start_time)

        msg.header(point_picker, "Choosing spectra...")
        inds = point_picker(self.grid, lon_all, lat_all)

        if len(inds) < 1:
            msg.warning("PointPicker didn't find any points. Aborting import of boundary.")
            return

        msg.header(boundary_reader, "Loading boundary spectra...")
        time, freq, dirs, spec, lon, lat, source = boundary_reader(start_time, end_time, inds)

        self.data = self.compile_to_xr(time, freq, dirs, spec, lon, lat, source)
        self.mask = [True]*len(self.x())

        # E.g. are the spectra oceanic convention etc.
        self._convention = boundary_reader.convention()

        return


    def process_boundary(self, boundary_processors: List[BoundaryProcessor]=[Multiply(calib_spec = 1)]):
        """Process all the individual spectra of the boundary object.

        E.g. change convention form WW3 to Oceanic, interpolate spectra to
        new directional grid, or multiply everything with a constant.
        """

        if not isinstance(boundary_processors, list):
            boundary_processors = [boundary_processors]

        convention_warning = False

        for processor in boundary_processors:

            msg.process(f"Processing spectra with {type(processor).__name__}")
            self._history.append(copy(processor))
            old_convention = processor._convention_in()
            if old_convention is not None:
                if old_convention != self.convention():
                    msg.warning(f"Boundary convention ({self.convention()}) doesn't match that expected by the processor ({old_convention})!")
                    convention_warning=True


            new_spec, new_dirs, new_freq = processor(self.spec(), self.dirs(), self.freq())


            self.data.spec.values = new_spec
            self.data = self.data.assign_coords(dirs=new_dirs)
            self.data = self.data.assign_coords(freq=new_freq)

            # Set new convention if the processor changed it
            new_convention = processor._convention_out()
            if new_convention is not None:
                self._convention = new_convention
                if convention_warning:
                    msg.warning(f"Convention variable set to {new_convention}, but this might be wrong...")
                else:
                    msg.info(f"Changing convention from {old_convention} >>> {new_convention}")

            print(processor)
            msg.blank()
        return


    def compile_to_xr(self, time, freq, dirs, spec, lon, lat, source):
        """Data from .import_boundary() is stored as an xarray Dataset."""

        x = np.array(range(spec.shape[1]))
        data = xr.Dataset(
            data_vars=dict(
                spec=(["time", "x", "freq", "dirs"], spec),
            ),
            coords=dict(
                freq=freq,
                dirs=dirs,
                x=x,
                lon=(["x"], lon),
                lat=(["x"], lat),
                time=time,
            ),
            attrs=dict(source=source,
                name=self.name()
            ),
            )
        return data

    def slice_data(self, start_time: str='', end_time: str='', x: List[int]=None) -> xr.Dataset:
        """Slice data in space (x) and time."""
        if not hasattr(self, data):
            return None

        if x is None:
            x=self.x()
        if not start_time:
            # This is not a string, but slicing works also with this input
            start_time = self.time()[0]
        if not end_time:
            # This is not a string, but slicing works also with this input
            end_time = self.time()[-1]
        sliced_data = self.data.sel(time=slice(start_time, end_time), x = x)
        return sliced_data

    def spec(self, start_time: str='', end_time: str='', x: List[int]=None) -> np.ndarray:
        """Slice spectra in space (x) and time."""
        spec = self.slice_data(start_time, end_time, x)
        if spec is None:
            return None
        return spec.spec.values

    def time(self):
        if not hasattr(self, 'data'):
            return pd.to_datetime([])
        return pd.to_datetime(self.data.time.values)

    def start_time(self) -> str:
        if len(self.time()) == 0:
            return ''
        return self.time()[0].strftime('%Y-%m-%d %H:%M')

    def end_time(self) -> str:
        if len(self.time()) == 0:
            return ''
        return self.time()[-1].strftime('%Y-%m-%d %H:%M')

    def dt(self) -> float:
        """ Returns time step of boundary spectra in hours."""
        if len(self.time()) == 0:
            return 0
        return self.time().to_series().diff().dt.total_seconds().values[-1]/3600

    def freq(self) -> np.ndarray:
        if not hasattr(self, 'data'):
            return np.array([])
        return copy(self.data.freq.values)

    def dirs(self) -> np.ndarray:
        if not hasattr(self, 'data'):
            return np.array([])
        return copy(self.data.dirs.values)

    def lon(self) -> np.ndarray:
        if not hasattr(self, 'data'):
            return np.array([])
        return copy(self.data.lon.values)

    def lat(self) -> np.ndarray:
        if not hasattr(self, 'data'):
            return np.array([])
        return copy(self.data.lat.values)

    def x(self) -> np.ndarray:
        if not hasattr(self, 'data'):
            return np.array([])
        return copy(self.data.x.values)

    def days(self):
        """Determins a Pandas data range of all the days in the time span."""
        if len(self.time()) == 0:
            return []
        return pd.date_range(start=self.time()[0].split('T')[0], end=self.time()[-1].split('T')[0], freq='D')

        #days = day_list(start_time = self.start_time, end_time = self.end_time)
        #return days

    def size(self):
        return (len(self.time()), len(self.x()))


    def name(self) -> str:
        """Return the name of the grid (set at initialization)."""
        return copy(self._name)

    def convention(self) -> str:
        """Returns the convention (WW3/Ocean/Met/Math) of the spectra"""
        if not hasattr(self, '_convention'):
            return None
        return copy(self._convention)

    def times_in_day(self, day):
        """Determines time stamps of one given day."""
        t0 = day.strftime('%Y-%m-%d') + "T00:00:00"
        t1 = day.strftime('%Y-%m-%d') + "T23:59:59"

        times = self.slice_data(start_time=t0, end_time=t1, x=[0])
        if times is None:
            return []

        return times.time.values

    def __str__(self) -> str:
        """Prints status of boundary."""

        msg.header(self, f"Status of boundary {self.name()}")
        msg.plain(f"Contains data ({len(self.x())} points) for {self.start_time()} - {self.end_time()}")
        msg.plain(f"Data covers: lon: {min(self.lon())} - {max(self.lon())}, lat: {min(self.lat())} - {max(self.lat())}")
        if len(self._history) > 0:
            msg.blank()
            msg.plain("Object has the following history:")
            for obj in self._history:
                msg.process(f"{obj.__class__.__bases__[0].__name__}: {type(obj).__name__}")

        msg.print_line()

        return ''
