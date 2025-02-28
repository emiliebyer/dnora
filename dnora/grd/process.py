import numpy as np
from abc import ABC, abstractmethod
from copy import copy

# Import auxility functions
from .. import msg

class GridProcessor(ABC):
    """Abstract class for modifying bathymetrical data of the Grid-object."""
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def __call__(self, data, lon, lat, land_sea_mask, boundary_mask):
        """Gets the bathymetrical information and returns a modified version.

        This method is called from within the Grid-object
        """
        pass

    @abstractmethod
    def __str__(self):
        """
        Describes how the data is processed.

        This is called by the Grid-objeect to provide output to the user.
        """
        pass


class TrivialFilter(GridProcessor):
    """Returns the identical data it is passed. Used as default option."""

    def __init__(self):
        pass

    def __call__(self, data, lon, lat, land_sea_mask, boundary_mask):
        return copy(data)

    def __str__(self):
        return("Doing nothing to the data, just passing it along.")

class SetMinDepth(GridProcessor):
    """Modify depth points shallower than a certain threshold.

    If to_land is True (default=False), then points shallower than min_depth
    are set to land. Otherwise the shallow points are set to min_depth.
    """

    def __init__(self, min_depth: float, to_land: bool=False):
        self.to_land = to_land
        self.min_depth = min_depth
        return

    def __call__(self, data, lon, lat, land_sea_mask, boundary_mask):
        shallow_points = data < self.min_depth

        if self.to_land:
            new_data = copy(data)
            new_data[np.logical_and(shallow_points, land_sea_mask)] = -999 # Don't touch land points by usign self.mask
            msg.plain(f"Affected {np.count_nonzero(np.logical_and(shallow_points, land_sea_mask))} points")
        else:
            # Set points to the limiter
            new_data = copy(data)
            new_data[np.logical_and(shallow_points, land_sea_mask)] = self.min_depth # Don't touch land points by usign self.mask
            msg.plain(f"Affected {np.count_nonzero(np.logical_and(shallow_points, land_sea_mask))} points")
        return new_data

    def __str__(self):
        if self.to_land:
            return(f"Setting points shallower than {self.min_depth} to land (-999)")
        else:
            return(f"Setting points shallower than {self.min_depth} to {self.min_depth}")
