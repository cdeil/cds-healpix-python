extern crate cdshealpix;
extern crate rayon;

// use cdshealpix::proj;
use cdshealpix::compass_point::MainWind;
use cdshealpix::nested::bmoc::*;
use cdshealpix::nested::{
    get_or_create,
    vertices,
    neighbours,
    cone_coverage_approx_custom,
    elliptical_cone_coverage_custom,
    polygon_coverage,
};

use rayon::prelude::*;

// Build
// see: https://github.com/getsentry/milksnake

// see: https://users.rust-lang.org/t/calling-into-rust-from-python/8923
// see: https://www.bignerdranch.com/blog/building-an-ios-app-in-rust-part-3/

pub fn to_slice<T>(ptr: *const T, len: usize) -> &'static [T] {
    assert!(!ptr.is_null());
    unsafe { std::slice::from_raw_parts(ptr, len) }
}

pub fn to_slice_mut<T>(ptr: *mut T, len: usize) -> &'static mut [T] {
    assert!(!ptr.is_null());
    unsafe { std::slice::from_raw_parts_mut(ptr, len) }
}

pub fn to_vec<T>(input: *mut T, len: usize) -> Vec<T> {
    assert!(!input.is_null());
    unsafe { Vec::from_raw_parts(input, len, len) }
}

#[no_mangle]
pub extern "C" fn hpx_hash_lonlat(
    depth: u8,
    num_coords: u32,
    lon: *const f64,
    lat: *const f64,
    ipixels: *mut u64,
) {
    let num_coords = num_coords as usize;

    let lon = to_slice(lon, num_coords);
    let lat = to_slice(lat, num_coords);

    let res = to_slice_mut(ipixels, num_coords);

    let layer = get_or_create(depth);
    for i in 0..num_coords {
        res[i] = layer.hash(lon[i], lat[i]);
    }
}

#[no_mangle]
pub extern "C" fn hpx_par_hash_lonlat(
    depth: u8,
    num_coords: u32,
    lon: *const f64,
    lat: *const f64,
    ipixels: *mut u64,
) {
    let num_coords = num_coords as usize;

    let lon = to_slice(lon, num_coords);
    let lat = to_slice(lat, num_coords);

    let res = to_slice_mut(ipixels, num_coords);

    // To control the number of threads, put this in a dedicated method?
    // rayon::ThreadPoolBuilder::new().num_threads(22).build_global().unwrap();
    
    let layer = get_or_create(depth);
    res.par_iter_mut().enumerate()
      .for_each(|(i, r)| *r = layer.hash(lon[i], lat[i]));
}

/// We do not return an array of LonLat not to have to explicitly call a function
/// to free the memory on the Python side.
#[no_mangle]
pub extern "C" fn hpx_center_lonlat(
    depth: u8,
    num_ipixels: u32,
    ipixels: *const u64,
    center_coords: *mut f64,
) {
    let num_ipixels = num_ipixels as usize;

    let hashs = to_slice(ipixels, num_ipixels);
    let res = to_slice_mut(center_coords, num_ipixels << 1);

    let layer = get_or_create(depth);

    for i in (0..res.len()).step_by(2) {
        let (l, b) = layer.center(hashs[i >> 1]);
        res[i] = l;
        res[i + 1] = b;
    }
}

/// The given array must be of size 8
/// [Slon, Slat, Elon, Elat, Nlon, Nlat, Wlon, Wlat]
#[no_mangle]
pub extern "C" fn hpx_vertices_lonlat(
    depth: u8,
    num_ipixels: u32,
    ipixels: *const u64,
    vertices_coords: *mut f64,
) {
    let num_ipixels = num_ipixels as usize;
    let res = to_slice_mut(vertices_coords, num_ipixels << 3);
    let ipixels = to_slice(ipixels, num_ipixels);

    for i in 0..num_ipixels {
        let ipix = ipixels[i];
        let [(s_lon, s_lat), (e_lon, e_lat), (n_lon, n_lat), (w_lon, w_lat)] =
            vertices(depth, ipix);
        let off = i << 3;

        res[off] = s_lon;
        res[off + 1] = s_lat;
        res[off + 2] = e_lon;
        res[off + 3] = e_lat;
        res[off + 4] = n_lon;
        res[off + 5] = n_lat;
        res[off + 6] = w_lon;
        res[off + 7] = w_lat;
    }
}

use std::panic;
/// The given array must be of size 9
/// `[S, SE, E, SW, C, NE, W, NW, N]`
#[no_mangle]
pub extern "C" fn hpx_neighbours(depth: u8, num_ipixels: u32, ipixels: *const u64, res: *mut i64) {
    let num_ipixels = num_ipixels as usize;
    let ipixels = to_slice(ipixels, num_ipixels);

    let res = to_slice_mut(res, 9 * num_ipixels);
    for i in 0..num_ipixels {
        let ipix = ipixels[i];
        let neig_map = neighbours(depth, ipix, true);

        let off = i * 9;
        res[off] = to_i64(neig_map.get(MainWind::S));
        res[off + 1] = to_i64(neig_map.get(MainWind::SE));
        res[off + 2] = to_i64(neig_map.get(MainWind::E));
        res[off + 3] = to_i64(neig_map.get(MainWind::SW));
        res[off + 4] = ipix as i64;
        res[off + 5] = to_i64(neig_map.get(MainWind::NE));
        res[off + 6] = to_i64(neig_map.get(MainWind::W));
        res[off + 7] = to_i64(neig_map.get(MainWind::NW));
        res[off + 8] = to_i64(neig_map.get(MainWind::N));
    }
}

fn to_i64(val: Option<&u64>) -> i64 {
    match val {
        Some(&val) => val as i64,
        None => -1_i64,
    }
}

// https://doc.rust-lang.org/1.7.0/src/libc/lib.rs.html#109

#[derive(Debug)]
#[repr(C)]
pub struct PyBMOC {
    len: u32,
    cells: Vec<BMOCCell>,
}

#[derive(Debug)]
#[repr(C)]
pub struct BMOCCell {
    depth: u8,
    hash: u64,
    flag: u8,
}

#[no_mangle]
pub extern "C" fn bmoc_free(ptr: *mut PyBMOC) {
    if !ptr.is_null() {
        unsafe {
            Box::from_raw(ptr)
            // Drop the content of the PyBMOC here.
        };
    }
}

fn to_bmoc_cell_array(bmoc: BMOC) -> Vec<BMOCCell> {
    let n_elems = bmoc.entries.len();
    let mut cells: Vec<BMOCCell> = Vec::with_capacity(n_elems);
    for raw_value in bmoc.entries.iter() {
        let cell = bmoc.from_raw_value(*raw_value);
        cells.push(BMOCCell {
            depth: cell.depth,
            hash: cell.hash,
            flag: cell.is_full as u8,
        });
    }
    // Free the cells which are not occupied
    cells.shrink_to_fit();
    cells
}

fn to_bmoc_flat_cell_array(bmoc: BMOC) -> Vec<BMOCCell> {
    let bmoc_flat = bmoc.flat_iter();
    let mut cells: Vec<BMOCCell> = Vec::with_capacity(bmoc_flat.deep_size());

    for cell in bmoc.flat_iter_cell() {
        cells.push(BMOCCell {
            depth: cell.depth,
            hash: cell.hash,
            flag: cell.is_full as u8
        });
    }
    // Free the cells which are not occupied
    cells.shrink_to_fit();
    cells
}

#[no_mangle]
pub extern "C" fn hpx_query_cone_approx(
    depth: u8,
    delta_depth: u8,
    lon: f64,
    lat: f64,
    radius: f64,
    flat: bool
) -> *const PyBMOC {
    let bmoc = cone_coverage_approx_custom(
        depth,
        delta_depth,
        lon,
        lat,
        radius,
    );

    let cells: Vec<BMOCCell>;
    if flat {
        cells = to_bmoc_flat_cell_array(bmoc);
    } else {
        cells = to_bmoc_cell_array(bmoc);
    }

    let len = cells.len() as u32;
    let bmoc = Box::new(PyBMOC { len, cells });
    Box::into_raw(bmoc)
}

#[no_mangle]
pub extern "C" fn hpx_query_elliptical_cone_approx(
    depth: u8,
    delta_depth: u8,
    lon: f64,
    lat: f64,
    a: f64,
    b: f64,
    pa: f64,
    flat: bool
) -> *const PyBMOC {
    let bmoc = elliptical_cone_coverage_custom(
        depth,
        delta_depth,
        lon,
        lat,
        a,
        b,
        pa,
    );

    let cells: Vec<BMOCCell>;
    if flat {
        cells = to_bmoc_flat_cell_array(bmoc);
    } else {
        cells = to_bmoc_cell_array(bmoc);
    }

    let len = cells.len() as u32;
    let bmoc = Box::new(PyBMOC { len, cells });
    Box::into_raw(bmoc)
}

#[no_mangle]
pub extern "C" fn hpx_query_polygon(
    depth: u8,
    n_vertices: u32,
    lon: *mut f64,
    lat: *mut f64,
    flat: bool
) -> *const PyBMOC {
    let n_vertices = n_vertices as usize;

    let lon = to_slice(lon, n_vertices);
    let lat = to_slice(lat, n_vertices);

    let mut vertices: Vec<(f64, f64)> = Vec::with_capacity(n_vertices);
    for i in 0..n_vertices {
        vertices.push((lon[i], lat[i]));
    }

    // Exact polygon
    let bmoc = polygon_coverage(depth, &vertices.into_boxed_slice(), true);
    let cells: Vec<BMOCCell>;
    if flat {
        cells = to_bmoc_flat_cell_array(bmoc);
    } else {
        cells = to_bmoc_cell_array(bmoc);
    }

    let len = cells.len() as u32;
    let bmoc = Box::new(PyBMOC { len, cells });
    Box::into_raw(bmoc)
}
