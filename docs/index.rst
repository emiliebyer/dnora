.. dnora documentation master file, created by
   sphinx-quickstart on Sun Nov 15 14:18:36 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to dnora's documentation!
=====================================
**dnora** is a Python package for dynamical downscaling of NORA wave hindcast using the spectral wave models SWAN or WAVEWATCH III and wave-flow model SWASH. 

The package contains functions that: 
  * create a high-resolution grid using open-access bathymetry/topography datasets (e.g., Emodnet 2018 bathymetry)
  * prepare the boundary conditions (NORA3, WAM4-operational wave model at MET Norway, available in https://thredds.met.no/thredds/catalog.html) for the spectral model
  * prepare the wind (NORA3, WAM4) forcing for the spectral model 
  * create input parameter files (e.g., .swn, .inp, .sws) for the models
  * run the wave model

Installing **dnora**
=============================================
1. Install anaconda3 or miniconda3
2. Clone dnora:

.. code-block:: bash

   $ git clone https://github.com/KonstantinChri/dnora.git
   $ cd dnora/

3. Create environment with the required dependencies and install dnora

.. code-block:: bash

  $ conda config --add channels conda-forge
  $ conda env create -f environment.yml
  $ conda activate dnora


Dependencies
=====================================
1. Installation of **SWAN**. The latest SWAN version can be downloaded from https://sourceforge.net/projects/swanmodel/files/swan/. The installation procedure can be found in: https://swanmodel.sourceforge.io/online_doc/swanimp/node4.html

2. Installation of **SWASH**. The latest SWASH version can be downloaded from https://sourceforge.net/projects/swash/. The installation procedure can be found in: https://swash.sourceforge.io/online_doc/swashimp/node4.html

To run the models within dnora, the paths, where the models are installed, need to be defined in .bashrc, e.g., ::

   export PATH=${PATH}:/home/user/Programs/swan
   export PATH=${PATH}:/home/user/Programs/swash

.. code-block:: rst

3. Fimex is a the File Interpolation, Manipulation and EXtraction library for gridded geospatial data (more info in \url{httpshttps://wiki.met.no/fimex/start}). Fimex is applied in DNORA for the preparation of forcing fields (wind and current). In case of running the spectral model without wind forcing, the fimex installation can be neglected.  A detailed installation procedure can be find in https://wiki.met.no/fimex/install. For a quick installation in linux-Ubuntu, you can follow the steps: open the Synaptic Package Manager (add ppa:met-norway/fimex to your system's Software Sources, see https://launchpad.net/~met-norway/+archive/ubuntu/fimex), search and mark for installation a latest version of fimex, apply installation and check the installation (usually it is installed in /usr/bin/) by typing in command line: fimex or fimex-xxx where xxx is the version number. In case that only fimex-xxx works then add a symbolic link::

      cd /usr/bin 
      sudo ln -s fimex-xxx fimex

.. code-block:: rst

Creating a Grid-object
=====================================
This section document the grd-module. The grid object is initialized with the following command::

   grid = grd.Grid(lon=(lon_min, lon_max), lat=(lat_min, lat_max), name=’GridName’)

.. code-block:: rst

Use ``print(grid)`` to print out the status of the object.

A desired grid spacing can be set either by providing a desired grid spacing in metres (approximate) or defining the amounts of grid points (exact)::

   grid.set_spacing(dm=250) # Set spacing to around 250 metres
   grid.set_spacing(nx=291, ny=249) # Create 291 (lon) x 249 (lat) grid points

.. code-block:: rst

Both  of  these  options  will  convert  the  input  to  the  native  resolution  in  longitude  andlatitude.  These can, of course, also be set directly by::
   
   grid.set_spacing(dlon=0.0048780, dlat=0.0022573)
   
.. code-block:: rst

In this case ``dlon`` and ``dlat`` are not exact.  If an exact resolution needs to be forced, the ``floating_edge``-option can be used, e.g.,::

   grid.set_spacing(dlon=1/205, dlat=1/443, floating_edge=True)
   
.. code-block:: rst
   
This will enforce the resolution and instead change the initially set ``lon_max`` and ``lat_max`` slightly (if needed). The main properties of the grid can be accessed by methods::

   grid.lon() # Longitude vector
   grid.lat() # Latitude vector
   grid.name() # Name given at initialization
   grid.nx() # Amount of point in longitude direction
   grid.ny() # Amount of point in latitude direction
   grid.size() # Tuple (nx, ny)
   
.. code-block:: rst

Setting boundary points
=====================================

Setting boundary points is now only important for being able to write the grid-files, but are also of consequence when importing boundary spectra. The central method is to set the edged of the grid to boundary points::

   bnd_set = grd.boundary.EdgesAsBoundary(edges=['N', 'W', 'S'])
   grid.set_boundary(boundary_setter=bnd_set)

.. code-block:: rst

Here the North, West, and South edges are set to boundary points, and this is suitable for e.g. WAVEWATCH III. In SWAN we might want to not set every edge point as a boundary point (and then let the wave model interpolate spectra), especially if the boundary spectra are only available at a coarse resolution. This can be done by initializing the boundary_setter as (every tenth point a boundary point)::

   bnd_set = grd.boundary.EdgesAsBoundary(edges=['N', 'W', 'S'], step=10)

.. code-block:: rst

Information about the boundary points that are set in the grid can be accessed using methods::

   grid.boundary_mask() # Boolean array where True is a boundary point
   grid.boundary_points() # Array containing a longitude, latitude list of the boundary points
   
.. code-block:: rst


Importing bathymetrical data
=====================================

The main idea is that the Grid-object is created, and a fixed set of methods are used to import a topography, mesh it down to a grid, or filter the data. The functionality of these methods are controlled by passing them a callable object. Adding e.g. a topography source thus means adding a new ``TopoReader``-class that can then me passed to the ``Grid``-object’s ``.import_topo()``-method. For now, only the ``EMODNET2018``-reader is available::

   grid.import_topo(topo_reader=grd.read.EMODNET2018(tile='D5'))

.. code-block:: rst

where the tile defines the geographical area (default 'C5'). This "raw" data can be processed by the ``.process_topo()`` command, taking a ``GridProcessor`` object. The data can me meshed to the desired grid definition by::

   grid.mesh_grid()
   
.. code-block:: rst

The default (and currently only available) ``GridMesher`` uses interpolation, and is set as default. After meshing the grid data can also be processed with a ``GridProcessor``. For example, to set all depth below 1 metre to land and after that impose a minimum of 2 metre depth in wet points, use::

   grid.process_grid(grd.process.SetMinDept(min_depth=1, to_land=True))
   grid.process_grid(grd.process.SetMinDept(min_depth=2))
  
.. code-block:: rst


Creating a ModelRun-object
=====================================

The ``ModelRun``-object is the second central object and contain all forcing and boundary data. This object is always defined for a certain grid and a certain time::

   model = mdl.ModelRun(grid, start_time='2018-08-25T00:00', end_time='2018-08-25T01:00')

.. code-block:: rst

The grid data can now be exported in a certain format using a ``GridWriter``. To export in WAVEWATCH III format::

   model.export_grid(grd.write.WW3())

.. code-block:: rst

Boundary and Forcing data can be read using ``BoundaryReaders`` and ``ForcingReaders``. To read in boundary spectra and wind forcing from the MET Norway NORA3 hindcast, use::

   model.import_boundary(bnd.read_metno.NORA3(), point_picker=bnd.pick.Area())
   model.import_forcing(wnd.read_metno.NORA3())

.. code-block:: rst

Here, the ``PointPicker`` object defines how spectra are chosen from the database. In WW3, we take all spectra around the grid area, and let WW3 interpolate. For SWAN, we would want to use::

   model.import_boundary(bnd.read_metno.NORA3(), point_picker=bnd.pick.NearestGridPoint())

.. code-block:: rst

to connect each defined boundary point to a certain spectra (even though we can get duplicates).

to write the boundary spectra in WAVEWATCH III format and wind forcing in SWAN format, use::

   model.export_boundary(bnd.write.WW3())
   model.export_forcing(wnd.write.SWAN())

.. code-block:: rst

The spectral convention is defined in the ``BoundaryReader`` and ``BoundaryWriter``, and the ``ModelRun``-object automatically takes care of convention changes (if needed).

**NB!** The WW3 convention here is thath of the WW3 *output* files, i.e. directional vector looks like a mathematical convention, but it is actually oceanic. This is in line with the bounc.ftn file used in the develop-branch of WAVEWATCH III.

Creating templates
=====================================

Several features that are typically used together can be packaged as a "template" by creating a subclass of the ``ModelRun`` object. These are defined in the ``mdl/models.py``-file. For example, a ``WW3``-template is defined as::

   class WW3(ModelRun):
       def _get_boundary_writer(self):
           return bnd.write.WW3()

       def _get_forcing_writer(self):
           return wnd.write.WW3()

       def _get_point_picker(self):
           return bnd.pick.Area()

       def _get_grid_writer(self):
           return grd.write.WW3()

.. code-block:: rst

These defaults can be used by::

   model = mdl.WW3(grid, start_time='2018-08-25T00:00', end_time='2018-08-25T01:00')
   
   model.import_boundary(bnd.read_metno.NORA3()) # PointPicker defined in template
   model.export_boundary() # BoundaryWriter defined in template
   
.. code-block:: rst

Further subclasses can also be defied. For example to have a ``ModelRun``-object that uses WW3 conventions and gets the forcing data from the NORA3-hindcast, a ``WW3_NORA3``-template is defined using the above ``WW3``-template::

   class WW3_NORA3(WW3):
       def _get_boundary_reader(self):
           return bnd.read_metno.NORA3()

       def _get_forcing_reader(self):
           return wnd.read_metno.NORA3()
        
.. code-block:: rst

The above importing and exporting of NORA3 boundary is now simplified to::

   model = mdl.WW3_NORA3(grid, start_time='2018-08-25T00:00', end_time='2018-08-25T01:00')
   
   model.import_boundary() # BoundaryReader and PointPicker defined in template
   model.export_boundary() # BoundaryWriter defined in template
.. code-block:: rst

The defaults of the templates can always be overridden by explicitly providing an object to the method. For example, the following code import WAM 4km boundary spectra, not NORA3 spectra::

   model = mdl.WW3_NORA3(grid, start_time='2018-08-25T00:00', end_time='2018-08-25T01:00')
   
   model.import_boundary(bnd.read_metno.WAM4km()) # Override BoundaryReader but use template PointPicker
   model.export_boundary() # BoundaryWriter defined in template
.. code-block:: rst



Run the spectral model
=====================================

This fucntionality is at the moment only available for SWAN and SWASH. To run the model automatically we first need to generate an input file::

   model.write_input_file(inp.SWAN())

.. code-block:: rst

This generates an input file based on the grid, boundary and forcing data that is available in the object. After that, the model can be automatically ran by::


   model.run_model(run.SWAN())

.. code-block:: rst

File names and directories
=====================================

The default file names and directories used in dnora are defined in the ``defaults.py``-file. Different default can be generated for different models, but the styles are not inherently linked to a certain models (see example below).

The default file names and folders used by the different writers are set within the writers, and they convey their preference to the ``ModelRun``-object. These defaults are used if the user doesn't provide anything explicitly. For example, the default file name for writing wind forcing for the SWAN model is::

   wind#Forcing#Grid#T0_#T1.asc


.. code-block:: rst

where ``#Forcing`` and ``#Grid`` will be replaced by the name of the forcing and grid of the ``ModelRun``-object, and ``#T0`` and ``#T1`` will be replaced by the start and end times, formatted according to the default format: ``%Y%m%d``.

Let's say we want to run an operation version of the SWAN model for the grid name "Sula", and want to have the forcing file name in the format: ``WIND_Sula_2018010106Z.asc``, where the time is the start time. The first way to do this is to provide this information to the method doing the writing, e.g.::

   model.export_forcing(wnd.write.SWAN(), filestring="WIND_#Grid_#T0Z.asc", datestring="%Y%m%d%H")

.. code-block:: rst

If this is used often, then these values can be added to ``defaults.py`` under the name "SWAN_oper". Then we can simply set the preference format upon initialization of the ``ForcingWriter``::

   model.export_forcing(wnd.write.SWAN(out_format='SWAN_oper'))

.. code-block:: rst

The third level is to actualy create a new template for this type of model runs, which can be done (for example) as a subclass of the ``SWAN``-template::

   class SWAN_oper(SWAN):
       def _get_forcing_writer(self):
           return wnd.write.SWAN(out_format='SWAN_oper')
           
.. code-block:: rst


.. toctree::
   :maxdepth: 2
   :caption: Contents:



