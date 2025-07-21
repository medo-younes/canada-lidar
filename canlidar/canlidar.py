# import laspy 

import os
import geopandas as gpd
import re
from geopy.geocoders import Nominatim
from shapely.geometry import Point, box
from util import find_year
import pygadm
class PathConfig():
    def __init__(self):
        self.root = '../'
        self.data = os.path.join(self.root, 'data')
        self.tile_index_fp = os.path.join(self.data, 'tile_index', 'tile_index.shp')

        self.test_bbox_fp = os.path.join(self.data, 'test_bbox.geojson')

class CanadaLIDAR():
    def __init__(self, project_name):
        self.project_name = project_name
        self.pt = PathConfig()
        self.tile_index_crs = "EPSG:4617"

        


    def read_tile_index(self, bbox_gdf = None):
        if bbox_gdf is not None:
            bbox_gdf = bbox_gdf.to_crs(self.tile_index_crs)
      

        tile_index_gdf = gpd.read_file(self.pt.tile_index_fp, bbox=bbox_gdf)
        

        # Get Project Year
        project_year = tile_index_gdf.Project.apply(lambda x: [v for v in x.split("_") if v.isdigit()])
        tile_index_gdf['project_year'] = project_year.apply(lambda x: x[0] if len(x) > 0 else None)

        ## Get Tile Year
        tile_year = tile_index_gdf.Tile_name.apply(lambda x: [find_year(y) for y in re.findall(r'\d+' ,x) if find_year(y) is not None])
        tile_index_gdf['tile_year'] = tile_year.apply(lambda x: x[0] if len(x) > 0 else None)

        ## Get URL Year
        tile_index_gdf['url_year'] = tile_index_gdf.URL.apply(lambda x: max(re.findall(r'\d+' ,x.split('/')[-1])) ).astype(int)
        tile_index_gdf['url_year'] = tile_index_gdf.url_year.apply(lambda x: find_year(x))

        tile_index_gdf['year'] = tile_index_gdf['project_year'].combine_first(tile_index_gdf['url_year']).combine_first(tile_index_gdf['tile_year'])
        
        return tile_index_gdf


    def query_bbox(self, bbox_gdf=None, bbox=None, year = None, test = False, return_df = False):
        '''
        bbox_gdf: GeoDataFrame of bounding box
        bbox = [minx, miny, maxx, maxy]
        
        '''

        if bbox_gdf is None or bbox is None:
            test = True
        else:
            bbox_gdf = bbox_gdf.to_crs(self.tile_index_crs)

        if test:
            bbox_gdf = gpd.read_file(self.pt.test_bbox_fp)

        # Read Tiles GeoParquet as GeoDataFrame
        tile_index = self.read_tile_index(bbox_gdf=bbox_gdf)
        
                
        if len(tile_index) > 0:
            

            if return_df:
                return tile_index
            
            else:
                return construct_query(tile_index,bbox_gdf, year, return_df)
                
        else: 
            return None

        
    def query_address(self, address=None, distance_km = None, year = None, test = False, return_df = False):
        
        if address is not None and test:
            address = 'Toronto, Canada'

        if distance_km is not None:
            d = distance_km * 1000
            geolocator = Nominatim(user_agent="canada-lidar")
            location = geolocator.geocode(address)
            if location is not None:
                x = location.longitude
                y = location.latitude
                point = Point(x,y)
                point_gdf = gpd.GeoDataFrame(geometry=[point], crs = 4326)
                utm_crs = point_gdf.estimate_utm_crs()
                point_gdf_local_crs = point_gdf.to_crs(utm_crs)
                x, y = point_gdf_local_crs.geometry[0].x,  point_gdf_local_crs.geometry[0].y
                bbox_coords = [x -d, y- d, x+d, y+d]
                bbox_gdf = gpd.GeoDataFrame(geometry=[box(*bbox_coords)], crs = utm_crs)
              
            else:
                print('Geocode Query Failed, adjust input address')

            

        ## Query Tile Index
        tile_index = self.read_tile_index(bbox_gdf=bbox_gdf)
        within_bounds = len(tile_index) > 0

        # Check if query is within bounds of tile index
        if within_bounds:
            if return_df:
                return tile_index
            else:
                return construct_query(tile_index, bbox_gdf, year, return_df)
        else:
            print(f'- Queried address is not within coverage area')
            return None

    
    def query_city(self, city, year= None, test = False, return_df= False):
        try:
            city_gdf = pygadm.Items(name=city)
            city_gdf = city_gdf.set_crs(4326)
            tile_index = self.read_tile_index(bbox_gdf=city_gdf)
            return construct_query(tile_index, city_gdf, year, return_df)
        except:
            print(f'{city} is not a valid geogreaphic administrative area')

    
    def query_tile(self, tile_id):
        return None
    
    def query_summary(self, query):
        print('QUERY SUMMARY')
        print('=======================')
        print(f'Address: {query['address']}')
        print(f'Query Area (km2): {query['query_area_km2'].round(2)}')
        print(f'Bounding Box Area: {query['bbox_area_km2'].round(2)}')
        print(f'Number of Tiles: {query['tile_count']}')
        print(f'LAZ File Count: {query['file_count']}')
        print(f'Available Years: {query['years']}')




def construct_query(tile_index, bbox_gdf= None, year=None, return_df = False): 

    if year is not None:
        nearest_year = get_nearest_year(tile_index, year)
        tile_index = tile_index[tile_index.year == str(nearest_year)]

    utm_crs = bbox_gdf.estimate_utm_crs()
    tile_index_local_utm = tile_index.to_crs(utm_crs)
    


    if return_df:
        return tile_index
    else:
                ## Reverse Geocode Query
        centroid = bbox_gdf.to_crs(4326).centroid.iloc[0]
        geolocator = Nominatim(user_agent="canada-lidar")
        location = geolocator.reverse(f"{centroid.y}, {centroid.x}")
        years = [int(x) for x in list(tile_index.year.unique()) if x is not None]
        return  dict(       
                            query_area_m2 = tile_index_local_utm.area.sum(), 
                            query_area_km2 = tile_index_local_utm.area.sum() * 0.000001,
                            years = sorted(years),
                            file_count = len(tile_index),
                            tile_count = len(tile_index.Tile_name.unique()),
                            tile_ids = tile_index.Tile_name.unique(),
                            project_names = tile_index.Project.unique(),
                            city = location.raw.get('address').get('city'),
                            address = location.address,
                            
                            urls = tile_index.URL.to_list(),
                            bbox = bbox_gdf.total_bounds,
                            bbox_area_m2 = bbox_gdf.to_crs(utm_crs).area.sum(),
                            bbox_area_km2 = bbox_gdf.to_crs(utm_crs).area.sum()* 0.000001,
                            bbox_centroid = [centroid.x, centroid.y],
                            crs = tile_index.crs,
                            epsg_code = tile_index.crs.to_epsg(),
                            utm_crs = utm_crs,
                            providers = tile_index.Provider.unique()
                            
                        )



def get_nearest_year(tile_index, year):
    ti_years = tile_index.year.dropna().astype(int).unique()
    year_deltas = abs(ti_years - year)
    min_delta = min(year_deltas)
    min_idx = list(year_deltas).index(min_delta)
    return ti_years[min_idx]
