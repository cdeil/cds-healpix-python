from . import lib, ffi
from .bmoc import BMOCConeApprox, \
                  BMOCPolygon, \
                  BMOCEllipticalConeApprox

import astropy.units as u
from astropy.coordinates import SkyCoord, Angle
import numpy as np


# Raise a ValueError exception if the input 
# HEALPix cells array contains invalid values
def _check_ipixels(data, depth):
    npix = 12 * 4 ** (depth)
    if (data >= npix).any() or (data < 0).any():
        raise ValueError("The input HEALPix cells contains value out of [0, {0}[".format(npix))


def lonlat_to_healpix(lon, lat, depth, parallel=False):
    """Get the HEALPix indexes that contains specific sky coordinates

    The depth of the returned HEALPix cell indexes must be specified. This 
    method is wrapped around the `hash <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.hash>`__ 
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    lon : `astropy.units.Quantity`
        The longitudes of the sky coordinates.
    lat : `astropy.units.Quantity`
        The latitudes of the sky coordinates.
    depth : int
        The depth of the returned HEALPix cell indexes.
    parallel : bool, optional
        Enable parallelization. False by default.

    Returns
    -------
    ipix : `numpy.array`
        A numpy array containing all the HEALPix cell indexes stored as `np.uint64`.

    Raises
    ------
    ValueError
        When the number of longitudes and latitudes given do not match.

    Examples
    --------
    >>> from cdshealpix import lonlat_to_healpix
    >>> import astropy.units as u
    >>> import numpy as np
    >>> lon = [0, 50, 25] * u.deg
    >>> lat = [6, -12, 45] * u.deg
    >>> depth = 12
    >>> ipix = lonlat_to_healpix(lon, lat, depth)
    """
    # Handle the case of an uniq lon, lat tuple given by creating a
    # 1d numpy array from the 0d astropy quantities.
    lon = np.atleast_1d(lon.to_value(u.rad)).ravel()
    lat = np.atleast_1d(lat.to_value(u.rad)).ravel()

    if lon.shape != lat.shape:
        raise ValueError("The number of longitudes does not match with the number of latitudes given")

    num_ipixels = lon.shape[0]
    # Allocation of the array containing the resulting ipixels
    ipixels = np.zeros(num_ipixels, dtype=np.uint64)

    if parallel:
        lib.hpx_par_hash_lonlat(
            # depth
            depth,
            # num of ipixels
            num_ipixels,
            # lon, lat
            ffi.cast("const double*", lon.ctypes.data),
            ffi.cast("const double*", lat.ctypes.data),
            # result
            ffi.cast("uint64_t*", ipixels.ctypes.data)
        )
    else:
        lib.hpx_hash_lonlat(
            # depth
            depth,
            # num of ipixels
            num_ipixels,
            # lon, lat
            ffi.cast("const double*", lon.ctypes.data),
            ffi.cast("const double*", lat.ctypes.data),
            # result
            ffi.cast("uint64_t*", ipixels.ctypes.data)
        )

    return ipixels

def healpix_to_lonlat(ipixels, depth):
    """Get the longitudes and latitudes of the center of some HEALPix cells at a given depth.

    This method does the opposite transformation of `lonlat_to_healpix`.
    It's wrapped around the `center <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.center>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipixels : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    depth : int
        The depth of the HEALPix cells.

    Returns
    -------
    lon, lat : (`astropy.units.Quantity`, `astropy.units.Quantity`)
        The sky coordinates of the center of the HEALPix cells given as a longitude, latitude tuple.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 4^{29 - depth}[`.

    Examples
    --------
    >>> from cdshealpix import healpix_to_lonlat
    >>> import numpy as np
    >>> ipixels = np.array([42, 6, 10])
    >>> depth = 12
    >>> lon, lat = healpix_to_lonlat(ipixels, depth)
    """
    ipixels = np.atleast_1d(ipixels).ravel()
    _check_ipixels(data=ipixels, depth=depth)

    ipixels = ipixels.astype(np.uint64)
    
    num_ipixels = ipixels.shape[0]
    # Allocation of the array containing the resulting coordinates
    lonlat = np.zeros(num_ipixels << 1, dtype=np.float64)

    lib.hpx_center_lonlat(
        # depth
        depth,
        # num of ipixels
        num_ipixels,
        # ipixels data array
        ffi.cast("const uint64_t*", ipixels.ctypes.data),
        # result
        ffi.cast("double*", lonlat.ctypes.data)
    )

    lonlat = lonlat.reshape((-1, 2)) * u.rad
    lon, lat = lonlat[:, 0], lonlat[:, 1]

    return lon, lat

def healpix_to_skycoord(ipixels, depth):
    """Get the sky coordinates of the center of some HEALPix cells at a given depth.

    This method does the opposite transformation of `lonlat_to_healpix`.
    It is the equivalent of `healpix_to_lonlat` except that it returns `astropy.coordinates.SkyCoord` instead
    of `astropy.units.Quantity`.
    It's wrapped around the `center <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.center>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipixels : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    depth : int
        The depth of the HEALPix cells.

    Returns
    -------
    skycoord : `astropy.coordinates.SkyCoord`
        The sky coordinates of the center of the HEALPix cells given as a `~astropy.coordinates.SkyCoord` object.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 4^{29 - depth}[`.

    Examples
    --------
    >>> from cdshealpix import healpix_to_skycoord
    >>> import numpy as np
    >>> ipixels = np.array([42, 6, 10])
    >>> depth = 12
    >>> skycoord = healpix_to_skycoord(ipixels, depth)
    """
    lon, lat = healpix_to_lonlat(ipixels, depth)
    return SkyCoord(ra=lon, dec=lat, frame="icrs", unit="rad")

def healpix_vertices_lonlat(ipixels, depth):
    """Get the longitudes and latitudes of the vertices of some HEALPix cells at a given depth.

    This method returns the 4 vertices of each cell in `ipixels`.
    This method is wrapped around the `vertices <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.vertices>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipixels : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    depth : int
        The depth of the HEALPix cells.

    Returns
    -------
    lon, lat : (`astropy.units.Quantity`, `astropy.units.Quantity`)
        The sky coordinates of the 4 vertices of the HEALPix cells. `lon` and `lat` are each `~astropy.units.Quantity` instances
        containing a :math:`N` x :math:`4` numpy array where N is the number of HEALPix cell given in `ipixels`.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 4^{29 - depth}[`.

    Examples
    --------
    >>> from cdshealpix import healpix_vertices_lonlat
    >>> import numpy as np
    >>> ipixels = np.array([42, 6, 10])
    >>> depth = 12
    >>> lon, lat = healpix_vertices_lonlat(ipixels, depth)
    """
    ipixels = np.atleast_1d(ipixels).ravel()
    _check_ipixels(data=ipixels, depth=depth)

    ipixels = ipixels.astype(np.uint64)
    
    num_ipixels = ipixels.shape[0]
    # Allocation of the array containing the resulting coordinates
    lonlat = np.zeros(num_ipixels << 3, dtype=np.float64)

    lib.hpx_vertices_lonlat(
        # depth
        depth,
        # num of ipixels
        num_ipixels,
        # ipixels data array
        ffi.cast("const uint64_t*", ipixels.ctypes.data),
        # result
        ffi.cast("double*", lonlat.ctypes.data)
    )

    lonlat = lonlat.reshape((-1, 4, 2)) * u.rad
    lon, lat = lonlat[:, :, 0], lonlat[:, :, 1]

    return lon, lat

def healpix_vertices_skycoord(ipixels, depth):
    """Get the sky coordinates of the vertices of some HEALPix cells at a given depth.

    This method returns the 4 vertices of each cell in `ipixels`.
    This method is wrapped around the `vertices <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.vertices>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipixels : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    depth : int
        The depth of the HEALPix cells.

    Returns
    -------
    vertices : `astropy.coordinates.SkyCoord`
        The sky coordinates of the 4 vertices of the HEALPix cells. `vertices` is a `~astropy.coordinates.SkyCoord` object
        containing a :math:`N` x :math:`4` numpy array where N is the number of HEALPix cells given in `ipixels`.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 4^{29 - depth}[`.

    Examples
    --------
    >>> from cdshealpix import healpix_vertices_skycoord
    >>> import numpy as np
    >>> ipixels = np.array([42, 6, 10])
    >>> depth = 12
    >>> skycoord = healpix_vertices_skycoord(ipixels, depth)
    """
    lon, lat = healpix_vertices_lonlat(ipixels, depth)
    return SkyCoord(ra=lon, dec=lat, frame="icrs", unit="rad")

def healpix_neighbours(ipixels, depth):
    """Get the neighbouring cells of some HEALPix cells at a given depth.

    This method returns a :math:`N` x :math:`9` `np.uint64` numpy array containing the neighbours of each cell of the :math:`N` sized `ipixels` array.
    This method is wrapped around the `neighbours <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.neighbours>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipixels : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    depth : int
        The depth of the HEALPix cells.

    Returns
    -------
    neighbours : `numpy.array`
        A :math:`N` x :math:`9` `np.uint64` numpy array containing the neighbours of each cell.
        The :math:`5^{th}` element corresponds to the index of HEALPix cell from which the neighbours are evaluated.
        All its 8 neighbours occup the remaining elements of the line.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 4^{29 - depth}[`.

    Examples
    --------
    >>> from cdshealpix import healpix_neighbours
    >>> import numpy as np
    >>> ipixels = np.array([42, 6, 10])
    >>> depth = 12
    >>> neighbours = healpix_neighbours(ipixels, depth)
    """
    ipixels = np.atleast_1d(ipixels).ravel()
    _check_ipixels(data=ipixels, depth=depth)

    ipixels = ipixels.astype(np.uint64)
    
    num_ipixels = ipixels.shape[0]
    # Allocation of the array containing the neighbours
    neighbours = np.zeros(num_ipixels * 9, dtype=np.int64)
    
    lib.hpx_neighbours(
        # depth
        depth,
        # num of ipixels
        num_ipixels,
        # ipixels data array
        ffi.cast("const uint64_t*", ipixels.ctypes.data),
        # result
        ffi.cast("int64_t*", neighbours.ctypes.data)
    )

    neighbours = neighbours.reshape((-1, 9))

    return neighbours

def cone_search_lonlat(lon, lat, radius, depth, depth_delta=2, flat=False):
    """Get the HEALPix cells contained in a cone at a given depth.

    This method is wrapped around the `cone <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.cone_coverage_approx_custom>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    lon : `astropy.units.Quantity`
        Longitude of the center of the cone.
    lat : `astropy.units.Quantity`
        Latitude of the center of the cone.
    radius : `astropy.units.Quantity`
        Radius of the cone.
    depth : int
        Maximum depth of the HEALPix cells that will be returned.
    depth_delta : int, optional
        To control the approximation, you can choose to perform the computations at a deeper depth using the `depth_delta` parameter.
        The depth at which the computations will be made will therefore be equal to `depth` + `depth_delta`.
    flat : boolean, optional
        False by default (i.e. returns a consistent MOC). If True, the HEALPix cells returned will all be at depth indicated by `depth`.

    Returns
    -------
    cells : `numpy.array`
        A numpy structured array (see `the numpy doc <https://docs.scipy.org/doc/numpy/user/basics.rec.html>`__).
        The structure of a cell contains 3 attributes:

        * A `ipix` field being a np.uint64
        * A `depth` field being a np.uint32
        * A `fully_covered` (i.e. a boolean flag) field stored in a np.uint8

    Raises
    ------
    ValueError
        When one of `lat`, `lon` and `radius` contains more that one value.

    Examples
    --------
    >>> from cdshealpix import cone_search_lonlat
    >>> import astropy.units as u
    >>> cone = cone_search_lonlat(lon=0 * u.deg, lat=0 * u.deg, radius=10 * u.deg, depth=10)
    """
    if not lon.isscalar or not lat.isscalar or not radius.isscalar:
        raise ValueError('The longitude, latitude and radius must be '
                         'scalar Quantity objects')

    lon = lon.to_value(u.rad)
    lat = lat.to_value(u.rad)
    radius = radius.to_value(u.rad)

    cone = BMOCConeApprox(depth=depth, depth_delta=depth_delta, lon=lon, lat=lat, radius=radius, flat=flat)

    return cone.data

def polygon_search_lonlat(lon, lat, depth, flat=False):
    """Get the HEALPix cells contained in a polygon at a given depth.

    This method is wrapped around the `polygon_coverage <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.polygon_coverage>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    lon : `astropy.units.Quantity`
        The longitudes of the vertices defining the polygon.
    lat : `astropy.units.Quantity`
        The latitudes of the vertices defining the polygon.
    depth : int
        Maximum depth of the HEALPix cells that will be returned.

    Returns
    -------
    cells : `numpy.array`
        A numpy structured array (see `the numpy doc <https://docs.scipy.org/doc/numpy/user/basics.rec.html>`__).
        The structure of a cell contains 3 attributes:

        * A ipix value being a np.uint64
        * A depth value being a np.uint32
        * A fully_covered flag bit stored in a np.uint8

    Raises
    ------
    ValueError
        When `lon` and `lat` do not have the same dimensions.
    IndexError
        When less than 3 vertices (.i.e. defining at least a triangle) are given.

    Examples
    --------
    >>> from cdshealpix import polygon_search_lonlat
    >>> import astropy.units as u
    >>> import numpy as np
    >>> lon = np.random.rand(3) * 360 * u.deg
    >>> lat = (np.random.rand(3) * 178 - 89) * u.deg
    >>> depth = 12
    >>> poly = polygon_search_lonlat(lon, lat, depth)
    """
    lon = np.atleast_1d(lon.to_value(u.rad)).ravel()
    lat = np.atleast_1d(lat.to_value(u.rad)).ravel()

    if lon.shape != lat.shape:
        raise ValueError("The number of longitudes does not match with the number of latitudes given")

    num_vertices = lon.shape[0]

    if num_vertices < 3:
        raise IndexError("There must be at least 3 vertices in order to form a polygon")

    polygon = BMOCPolygon(depth=depth, num_vertices=num_vertices, lon=lon, lat=lat, flat=flat)

    return polygon.data

def elliptical_cone_search_lonlat(lon, lat, a, b, pa, depth, depth_delta=2, flat=False):
    """Get the HEALPix cells contained in an elliptical cone at a given depth.

    This method is wrapped around the `elliptical_cone_coverage_custom <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.elliptical_cone_coverage_custom>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    lon : `astropy.coordinates.Quantity`
        Longitude of the center of the elliptical cone.
    lat : `astropy.coordinates.Quantity`
        Latitude of the center of the elliptical cone.
    a : `astropy.coordinates.Angle`
        Semi-major axe angle of the elliptical cone.
    b : `astropy.coordinates.Angle`
        Semi-minor axe angle of the elliptical cone.
    pa : `astropy.coordinates.Angle`
        The position angle (i.e. the angle between the north and the semi-major axis, east-of-north).
    depth : int
        Maximum depth of the HEALPix cells that will be returned.
    depth_delta : int, optional
        To control the approximation, you can choose to perform the computations at a deeper depth using the `depth_delta` parameter.
        The depth at which the computations will be made will therefore be equal to `depth` + `depth_delta`.
    flat : boolean, optional
        False by default (i.e. returns a consistent MOC). If True, the HEALPix cells returned will all be at depth indicated by `depth`.

    Returns
    -------
    cells : `numpy.array`
        A numpy structured array (see `the numpy doc <https://docs.scipy.org/doc/numpy/user/basics.rec.html>`__).
        The structure of a cell contains 3 attributes:

        * A ipix value being a np.uint64
        * A depth value being a np.uint32
        * A fully_covered flag bit stored in a np.uint8

    Raises
    ------
    ValueError
        If one of `lon`, `lat`, `major_axe`, `minor_axe` or `pa` contains more that one value.
    ValueError
        If the semi-major axis `a` exceeds 90deg (i.e. area of one hemisphere)
    ValueError
        If the semi-minor axis `b` is greater than the semi-major axis `a`

    Examples
    --------
    >>> from cdshealpix import elliptical_cone_search_lonlat
    >>> import astropy.units as u
    >>> from astropy.coordinates import Angle, SkyCoord
    >>> import numpy as np
    >>> lon = 0 * u.deg
    >>> lat = 0 * u.deg
    >>> a = Angle(50, unit="deg")
    >>> b = Angle(10, unit="deg")
    >>> pa = Angle(45, unit="deg")
    >>> depth = 12
    >>> elliptical_cone = elliptical_cone_search_lonlat(lon, lat, a, b, pa, depth)
    """
    if not lon.isscalar or not lat.isscalar or not a.isscalar \
        or not b.isscalar or not pa.isscalar:
        raise ValueError('The longitude, latitude, semi-minor axe, semi-major axe and angle must be '
                         'scalar Quantity objects')

    if a >= Angle(np.pi/2.0, unit="rad"):
        raise ValueError('The semi-major axis exceeds 90deg.')

    if b > a:
        raise ValueError('The semi-minor axis is greater than the semi-major axis.')

    lon = lon.to_value(u.rad)
    lat = lat.to_value(u.rad)
    a = a.to_value(u.rad)
    b = b.to_value(u.rad)
    pa = pa.to_value(u.rad)

    elliptical_cone = BMOCEllipticalConeApprox(depth=depth,
        depth_delta=depth_delta,
        lon=lon,
        lat=lat,
        a=a,
        b=b,
        pa=pa,
        flat=flat)

    return elliptical_cone.data
