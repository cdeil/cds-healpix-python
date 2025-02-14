import pytest
import numpy as np

from astropy.coordinates import Angle, SkyCoord
import astropy.units as u

from ..ring import lonlat_to_healpix, skycoord_to_healpix, \
                   healpix_to_lonlat, \
                   healpix_to_xy, \
                   vertices

@pytest.mark.parametrize("size", [1, 10, 100, 1000, 10000])
def test_lonlat_to_healpix(size):
    depth = np.random.randint(30)
    nside = 1 << depth

    lon = np.random.rand(size) * 360 * u.deg
    lat = (np.random.rand(size) * 178 - 89) * u.deg

    ipixels, dx, dy = lonlat_to_healpix(lon=lon, lat=lat, nside=nside, return_offsets=True)
    ipixels, dx, dy = skycoord_to_healpix(
        SkyCoord(lon, lat, frame="icrs"),
        nside=nside,
        return_offsets=True,
    )

    npix = 12 * nside ** 2
    assert(((ipixels >= 0) & (ipixels < npix)).all())
    assert(((dx >= 0) & (dx <= 1)).all())

@pytest.mark.parametrize("lon, lat, expected_ipix", [
    (5*u.deg, 5*u.deg, 12),
    (180*u.deg, 5*u.deg, 16),
    (179*u.deg, -88*u.deg, 45)
])
def test_lonlat_to_healpix_accurate(lon, lat, expected_ipix):
    nside = 2
    ipixels, dx, dy = lonlat_to_healpix(lon=lon, lat=lat, nside=nside, return_offsets=True)

    assert ipixels == expected_ipix
    assert(((dx >= 0) & (dx <= 1)).all())
    assert(((dy >= 0) & (dy <= 1)).all())

@pytest.mark.parametrize("size", [1, 10, 100, 1000, 10000])
def test_healpix_to_lonlat(size):
    depth = np.random.randint(30)
    nside = 1 << depth

    ipixels = np.random.randint(12 * (nside ** 2), size=size, dtype="uint64")
    lon, lat = healpix_to_lonlat(ipix=ipixels, nside=nside)
    assert(lon.shape == lat.shape)

@pytest.mark.parametrize("nside", np.arange(start=1, stop=11))
def test_healpix_vs_lonlat(nside):
    size = 1000
    ipixels = np.random.randint(12 * nside * nside, size=size, dtype="uint64")
    lon, lat = healpix_to_lonlat(ipix=ipixels, nside=nside, dx=0.5, dy=0.5)

    ipixels_result, dx, dy = lonlat_to_healpix(lon=lon, lat=lat, nside=nside, return_offsets=True)
    assert((ipixels == ipixels_result).all())

@pytest.mark.parametrize("size", [1, 10, 100, 1000, 10000, 100000])
def test_healpix_to_xy_robust(size):
    depth = np.random.randint(30)
    nside = 1 << depth

    ipixels = np.random.randint(12 * (nside ** 2), size=size, dtype="uint64")
    x, y = healpix_to_xy(ipix=ipixels, nside=nside)
    assert(x.shape == y.shape)

@pytest.mark.parametrize("ipix, depth, expected_x, expected_y", [
    (np.arange(12), 0,
     np.array([1. , 3. , 5. , 7. , 0., 2., 4. , 6. , 1., 3., 5., 7.], dtype=np.float64),
     np.array([1., 1.,  1.,  1., 0., 0., 0., 0. ,-1, -1, -1, -1], dtype=np.float64)),
    ([], 0,
     np.array([], dtype=np.float64),
     np.array([], dtype=np.float64)),
    (0, 0,
     np.array([1.], dtype=np.float64),
     np.array([1.], dtype=np.float64))
])
def test_healpix_to_xy(ipix, depth, expected_x, expected_y):
    x, y = healpix_to_xy(ipix, 1 << depth)

    assert (x == expected_x).all()
    assert (y == expected_y).all()

@pytest.mark.parametrize("size", [1, 10, 100, 1000, 10000, 100000])
def test_vertices_lonlat(size):
    depth = np.random.randint(30)
    nside = 1 << depth

    ipixels = np.random.randint(12 * (nside ** 2), size=size, dtype=np.uint64)

    lon, lat = vertices(ipix=ipixels, nside=nside)
    assert(lon.shape == lat.shape)
    assert(lon.shape == (size, 4))
