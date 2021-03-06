'''Take slices of a geotiff by shapes from a shapefile

CC - BY - SA 2013 - Max Shron
'''

import Polygon
import numpy as np
import shapefile
import gdal
import sys
import yaml

def snap_to_grid(geotransform, lat, lon):
  '''lat/lon to nearest grid point (x,y)'''
  x = (lon - geotransform['top_left_x']) / geotransform['pixel_width']
  y = (lat - geotransform['top_left_y']) / geotransform['pixel_height']
  return (int(round(x)),int(round(y)))

def grid_to_center_latlon(geotransform, x, y):
  '''(x,y) to latlon'''
  lon = geotransform['top_left_x'] + geotransform['pixel_width']*(x+.5)
  lat = geotransform['top_left_y'] + geotransform['pixel_height']*(y+.5)
  return (lat, lon)

def slice_geotiff_by_shape(dataset, polygon, raster_band=1):
  '''Get a masked array corresponding to polygon from a GDal Dataset.

  Consider making this something which samples by NN instead, if the spaces are too small.
  
  This *assumes* a north-up map. If you want it to handle other ones, hack it in yourself.'''
  bbox = polygon.boundingBox()
  geotransform = dict(zip("top_left_x,pixel_width,foo,top_left_y,bar,pixel_height".split(","), dataset.GetGeoTransform()))
  top_left_pt = snap_to_grid(geotransform, bbox[3], bbox[0])
  bottom_right_pt = snap_to_grid(geotransform, bbox[2], bbox[1])
  array_width = np.abs(top_left_pt[0] - bottom_right_pt[0])
  array_height = np.abs(top_left_pt[1] - bottom_right_pt[1])
  out = np.ma.masked_array(np.zeros((array_height, array_width)), np.zeros((array_height, array_width)))
  for i in xrange(array_height):
    for j in xrange(array_width):
      exact_j = top_left_pt[0]+j
      exact_i = top_left_pt[1]+i
      lon, lat = grid_to_center_latlon(geotransform, exact_j, exact_i) 
      if polygon.isInside(lat,lon):
        out[i,j] = dataset.GetRasterBand(raster_band).ReadAsArray(exact_j,exact_i,1,1)
      else:
        out.mask[i,j] = 1

  return out

def shape_to_polygon(shape):
  out = Polygon.Polygon()
  if len(shape.parts) == 1:
    out += Polygon.Polygon(shape.points)
  else:
    parts = list(shape.parts) + [-1]
    for i in xrange(len(shape.parts)):
      out += Polygon.Polygon(shape.points[parts[i]:parts[i+1]])
  return out
        
def shapes_iter(geotiff_file, shapefile_file, raster_band = 1):
  '''Takes a filename of a geotiff, a filename of a shapefile, and an optional raster band within the geotiff and returns an iterable that gives the record for each shape in the shapefile along with a masked numpy array slice of the geotiff on that raster band covering the area in question'''
  d = gdal.OpenShared(geotiff_file)
  s = shapefile.Reader(shapefile_file)
  fields = [x[0] for x in s.fields[1:]]
  for i in xrange(s.numRecords):
    record = s.record(i)
    shape = s.shape(i)
    data = dict(zip(fields,record))
    p = shape_to_polygon(shape)
    data['raster-%i'%raster_band] = slice_geotiff_by_shape(d, p, raster_band)
    data['midpoint'] = p.center()
    yield data


def main(argv):
  shapefile_file = argv[1]
  geotiff_file = argv[2]
  for i,rez in enumerate(shapes_iter(geotiff_file, shapefile_file)):
    print yaml.dump({i: rez})


if __name__ == "__main__":
  main(sys.argv)


