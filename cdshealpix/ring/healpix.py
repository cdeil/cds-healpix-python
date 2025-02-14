from .. import cdshealpix # noqa

import astropy.units as u
from astropy.coordinates import SkyCoord, Angle
import numpy as np

# Raise a ValueError exception if the input 
# HEALPix cells array contains invalid values
def _check_ipixels(data, nside):
    npix = 12 * (nside ** 2)
    if (data >= npix).any() or (data < 0).any():
        raise ValueError("The input HEALPix cells contains value out of [0, {0}]".format(npix - 1))


def lonlat_to_healpix(lon, lat, nside, return_offsets=False):
    r"""Get the HEALPix indexes that contains specific sky coordinates

    The ``nside`` of the returned HEALPix cell indexes must be specified. This 
    method is wrapped around the `hash <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.hash>`__ 
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    lon : `astropy.units.Quantity`
        The longitudes of the sky coordinates.
    lat : `astropy.units.Quantity`
        The latitudes of the sky coordinates.
    nside : int
        The nside of the returned HEALPix cell indexes.
    return_offsets : bool, optional
        If set to `True`, returns a tuple made of 3 elements, the HEALPix cell
        indexes and the dx, dy arrays telling where the (``lon``, ``lat``) coordinates
        passed are located on the cells. ``dx`` and ``dy`` are :math:`\in [0, 1]`

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
    >>> from cdshealpix.ring import lonlat_to_healpix
    >>> import astropy.units as u
    >>> import numpy as np
    >>> lon = [0, 50, 25] * u.deg
    >>> lat = [6, -12, 45] * u.deg
    >>> depth = 12
    >>> ipix = lonlat_to_healpix(lon, lat, (1 << depth))
    """
    # Handle the case of an uniq lon, lat tuple given by creating a
    # 1d numpy array from the 0d astropy quantities.
    lon = np.atleast_1d(lon.to_value(u.rad))
    lat = np.atleast_1d(lat.to_value(u.rad))

    if nside < 1 or nside > (1 << 29):
        raise ValueError("nside must be in the [1, (1 << 29)[ closed range")

    if lon.shape != lat.shape:
        raise ValueError("The number of longitudes does not match with the number of latitudes given")

    num_ipix = lon.shape
    # Allocation of the array containing the resulting ipixels
    ipix = np.empty(num_ipix, dtype=np.uint64)
    dx = np.empty(num_ipix, dtype=np.float64)
    dy = np.empty(num_ipix, dtype=np.float64)

    cdshealpix.lonlat_to_healpix_ring(nside, lon, lat, ipix, dx, dy)

    if return_offsets:
        return ipix, dx, dy
    else:
        return ipix

def skycoord_to_healpix(skycoord, nside, return_offsets=False):
    r"""Get the HEALPix indexes that contains specific sky coordinates

    The ``nside`` of the returned HEALPix cell indexes must be specified.
    This method is wrapped around the
    `hash <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.hash>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    skycoord : `astropy.coordinates.SkyCoord`
        The sky coordinates.
    nside : int
        The nside of the returned HEALPix cell indexes.
    return_offsets : bool, optional
        If set to `True`, returns a tuple made of 3 elements, the HEALPix cell
        indexes and the dx, dy arrays telling where the (``lon``, ``lat``) coordinates
        passed are located in the cells. ``dx`` and ``dy`` are :math:`\in [0, 1]`

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
    >>> from cdshealpix.ring import skycoord_to_healpix
    >>> import astropy.units as u
    >>> from astropy.coordinates import SkyCoord
    >>> import numpy as np
    >>> skycoord = SkyCoord([0, 50, 25] * u.deg, [6, -12, 45] * u.deg, frame="icrs")
    >>> depth = 12
    >>> ipix = skycoord_to_healpix(skycoord, 1 << depth)
    """
    return lonlat_to_healpix(skycoord.icrs.ra, skycoord.icrs.dec, nside, return_offsets)

def healpix_to_lonlat(ipix, nside, dx=0.5, dy=0.5):
    r"""Get the longitudes and latitudes of the center of some HEALPix cells at a given depth.

    This method does the opposite transformation of `lonlat_to_healpix`.
    It's wrapped around the `center <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.center>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipix : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    nside : int
        The nside of the HEALPix cells.
    dx : float, optional
        The offset position :math:`\in [0, 1]` along the X axis. By default, `dx=0.5`
    dy : float, optional
        The offset position :math:`\in [0, 1]` along the Y axis. By default, `dy=0.5`

    Returns
    -------
    lon, lat : (`astropy.units.Quantity`, `astropy.units.Quantity`)
        The sky coordinates of the center of the HEALPix cells given as a longitude, latitude tuple.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 12` x :math:`N_{side} ^ 2[`.

    Examples
    --------
    >>> from cdshealpix.ring import healpix_to_lonlat
    >>> import numpy as np
    >>> ipix = np.array([42, 6, 10])
    >>> depth = 12
    >>> lon, lat = healpix_to_lonlat(ipix, 1 << depth)
    """
    if nside < 1 or nside > (1 << 29):
        raise ValueError("nside must be in the [1, (1 << 29)[ closed range")

    if dx < 0 or dx > 1:
        raise ValueError("dx must be between [0, 1]")

    if dy < 0 or dy > 1:
        raise ValueError("dy must be between [0, 1]")

    ipix = np.atleast_1d(ipix)
    _check_ipixels(data=ipix, nside=nside)
    ipix = ipix.astype(np.uint64)

    size_skycoords = ipix.shape
    # Allocation of the array containing the resulting coordinates
    lon = np.zeros(size_skycoords)
    lat = np.zeros(size_skycoords)

    cdshealpix.healpix_to_lonlat_ring(nside, ipix, dx, dy, lon, lat)
    return lon * u.rad, lat * u.rad

def healpix_to_skycoord(ipix, nside, dx=0.5, dy=0.5):
    r"""Get the sky coordinates of the center of some HEALPix cells at a given nside.

    This method does the opposite transformation of `lonlat_to_healpix`.
    It is the equivalent of `healpix_to_lonlat` except that it returns `astropy.coordinates.SkyCoord` instead
    of `astropy.units.Quantity`.
    It's wrapped around the `center <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.center>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipix : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    nside : int
        The nside of the HEALPix cells.
    dx : float, optional
        The offset position :math:`\in [0, 1]` along the X axis. By default, `dx=0.5`
    dy : float, optional
        The offset position :math:`\in [0, 1]` along the Y axis. By default, `dy=0.5`

    Returns
    -------
    skycoord : `astropy.coordinates.SkyCoord`
        The sky coordinates of the center of the HEALPix cells given as a `~astropy.coordinates.SkyCoord` object.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 12` x :math:`N_{side} ^ 2[`.

    Examples
    --------
    >>> from cdshealpix.ring import healpix_to_skycoord
    >>> import numpy as np
    >>> ipix = np.array([42, 6, 10])
    >>> depth = 12
    >>> skycoord = healpix_to_skycoord(ipix, 1 << depth)
    """
    lon, lat = healpix_to_lonlat(ipix, nside, dx, dy)
    return SkyCoord(ra=lon, dec=lat, frame="icrs", unit="rad")

def healpix_to_xy(ipix, nside):
    r"""
    Project the center of a HEALPix cell to the xy-HEALPix plane

    Parameters
    ----------
    ipix : `numpy.array`
        The HEALPix cells which centers will be projected
    nside : int
        The nside of the HEALPix cells

    Returns
    -------
    x, y: (`numpy.array`, `numpy.array`)
        The position of the HEALPix centers in the xy-HEALPix plane.
        :math:`x \in [0, 8[` and :math:`y \in [-2, 2]`

    Examples
    --------
    >>> from cdshealpix.ring import healpix_to_xy
    >>> import astropy.units as u
    >>> import numpy as np
    >>> depth = 0
    >>> ipix = np.arange(12)
    >>> x, y = healpix_to_xy(ipix, 1 << depth)
    """
    if nside < 1 or nside > (1 << 29):
        raise ValueError("nside must be in the [1, (1 << 29)[ closed range")

    ipix = np.atleast_1d(ipix)
    _check_ipixels(data=ipix, nside=nside)
    ipix = ipix.astype(np.uint64)

    x = np.zeros(ipix.shape, dtype=np.float64)
    y = np.zeros(ipix.shape, dtype=np.float64)
    cdshealpix.healpix_to_xy_ring(nside, ipix, x, y)

    return x, y

def vertices(ipix, nside, step=1):
    """Get the longitudes and latitudes of the vertices of some HEALPix cells at a given nside.

    This method returns the 4 vertices of each cell in `ipix`.
    This method is wrapped around the `vertices <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.vertices>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipix : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    nside : int
        The nside of the HEALPix cells.
    step : int, optional
        The number of vertices returned per HEALPix side. By default it is set to 1 meaning that
        it will only return the vertices of the cell. 2 means that it will returns the vertices of
        the cell plus one more vertex per edge (the middle of it). More generally, the number
        of vertices returned is ``4 * step``.

    Returns
    -------
    lon, lat : (`astropy.units.Quantity`, `astropy.units.Quantity`)
        The sky coordinates of the 4 vertices of the HEALPix cells. `lon` and `lat` are each `~astropy.units.Quantity` instances
        containing a :math:`N` x :math:`4` numpy array where N is the number of HEALPix cell given in `ipix`.

    Warnings
    --------
    ``step`` is currently not implemented for the ring scheme. Therefore it is set to 1 by default.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 12` x :math:`N_{side} ^ 2[`.

    Examples
    --------
    >>> from cdshealpix.ring import vertices
    >>> import numpy as np
    >>> ipix = np.array([42, 6, 10])
    >>> depth = 12
    >>> lon, lat = vertices(ipix, (1 << depth))
    """
    if nside < 1 or nside > (1 << 29):
        raise ValueError("nside must be in the [1, (1 << 29)[ closed range")

    if step < 1:
        raise ValueError("The number of step must be >= 1")

    ipix = np.atleast_1d(ipix)
    _check_ipixels(data=ipix, nside=nside)
    ipix = ipix.astype(np.uint64)

    # Allocation of the array containing the resulting coordinates
    lon = np.zeros(ipix.shape + (4 * step,))
    lat = np.zeros(ipix.shape + (4 * step,))

    cdshealpix.vertices_ring(nside, ipix, step, lon, lat)
    return lon * u.rad, lat * u.rad

def vertices_skycoord(ipix, nside, step=1):
    """Get the sky coordinates of the vertices of some HEALPix cells at a given nside.

    This method returns the 4 vertices of each cell in `ipix`.
    This method is wrapped around the `vertices <https://docs.rs/cdshealpix/0.1.5/cdshealpix/nested/struct.Layer.html#method.vertices>`__
    method from the `cdshealpix Rust crate <https://crates.io/crates/cdshealpix>`__.

    Parameters
    ----------
    ipix : `numpy.array`
        The HEALPix cell indexes given as a `np.uint64` numpy array.
    nside : int
        The nside of the HEALPix cells.
    step : int, optional
        The number of vertices returned per HEALPix side. By default it is set to 1 meaning that
        it will only return the vertices of the cell. 2 means that it will returns the vertices of
        the cell plus one more vertex per edge (the middle of it). More generally, the number
        of vertices returned is ``4 * step``.

    Returns
    -------
    vertices : `astropy.coordinates.SkyCoord`
        The sky coordinates of the 4 vertices of the HEALPix cells. `vertices` is a `~astropy.coordinates.SkyCoord` object
        containing a :math:`N` x :math:`4` numpy array where N is the number of HEALPix cells given in `ipix`.

    Raises
    ------
    ValueError
        When the HEALPix cell indexes given have values out of :math:`[0, 12` x :math:`N_{side} ^ 2[`.

    Examples
    --------
    >>> from cdshealpix.ring import vertices_skycoord
    >>> import numpy as np
    >>> ipix = np.array([42, 6, 10])
    >>> depth = 12
    >>> vertices = vertices_skycoord(ipix, 1 << depth)
    """
    lon, lat = vertices(ipix, nside, step)
    return SkyCoord(ra=lon, dec=lat, frame="icrs", unit="rad")