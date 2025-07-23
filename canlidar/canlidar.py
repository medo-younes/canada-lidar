# import laspy 

import os
import geopandas as gpd
import re
from geopy.geocoders import Nominatim
from shapely.geometry import Point, box
from util import find_year
import pygadm
from s3_download import download_laz_from_s3
from pdal_ops import *

class PathConfig():
    def __init__(self):
        self.root = '../'
        self.data = os.path.join(self.root, 'data')
        self.tile_index_fp = os.path.join(self.data, 'tile_index', 'tile_index.shp')
        self.test_bbox_fp = os.path.join(self.data, 'test_bbox.geojson')
        self.test_poly_fp = os.path.join(self.data, 'test_poly.geojson')

        self.lidar_data =  os.path.join(self.root, 'lidar_data')

class CanadaLiDAR():
    def __init__(self, project_name):
        self.project_name = project_name
        self.pt = PathConfig()
        self.tile_index_crs = "EPSG:4617"

        self.out_folder = os.path.join(self.pt.lidar_data, self.project_name)
        if os.path.exists(self.out_folder) == False:
            os.makedirs(self.out_folder)

    

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

    ## QUERY FUNCTIONS
    def query_bbox(self, bbox= None,year = None, test = False, return_df = False):
        '''
       
        bbox = [minx, miny, maxx, maxy]
        
        '''
        if test or bbox is None:
            gdf = gpd.read_file(self.pt.test_bbox_fp)
        else:
            gdf = gpd.GeoDataFrame(geometry = [box(*bbox)],crs = 4326)
        return self.query_polygon(gdf, year, test, return_df)

    def query_polygon(self, gdf=None,year = None, test = False, return_df = False):
        '''
        gdf: GeoDataFrame of Polygon or MultiPolygon
        '''
        if test or gdf is None:
            gdf = gpd.read_file(self.pt.test_poly_fp)
        else:
            gdf = gdf.to_crs(self.tile_index_crs)
      
        # Read Tiles GeoParquet as GeoDataFrame
        tile_index = self.read_tile_index(bbox_gdf=gdf)
         
        if len(tile_index) > 0:
            if return_df:
                return tile_index
            else:
                return self.build_query(gdf, year, return_df)
                
        else: 
            print('- No Tiles have matched your query')
            
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

        return self.build_query(bbox_gdf, year, return_df)
     

    
    def query_city(self, city, year= None, test = False, return_df= False):
        try:
            city_gdf = pygadm.Items(name=city)
            city_gdf = city_gdf.set_crs(4326)
            tile_index = self.read_tile_index(bbox_gdf=city_gdf)
       
    
            return self.build_query(city_gdf, year, return_df)
        except:
            print(f'{city} is not a valid geographic administrative area')

    
    def query_tile(self, tile_id):
        return None
    
    # DOWNLOAD FUNCTIONS
    def download(self, query, merge_all = False, clip = False, root = "../lidar_data"):
        
        out_folder = os.path.join(root, self.project_name)
        if os.path.exists(out_folder) == False:
            os.makedirs(out_folder)
        
        
        out_files = [os.path.join(out_folder, url.split('/')[-1]) for url in query['urls']]
        
        s3_urls = query["urls"]
        wkt = query['bbox_wkt']

        # Clip and Merge All Point Clouds
        if clip and merge_all:
            out_file = os.path.join(out_folder,  f"{self.project_name}_merged.copc.laz")
            stages = [reader('copc', url, polygon = wkt) for url in s3_urls]
            stages.append(merge())
            stages.append(writer('las', out_file))

        # Clip and download individual LAZ files
        elif clip and merge_all == False:
            stages = list()
            for url, out_file in zip(s3_urls, out_files):
                stages.append(reader('copc', url, polygon = wkt))
                stages.append(writer('las', out_file))
        
        # Merge all LAZ Files - no clipping
        elif clip == False and merge_all:
            out_file = os.path.join(out_folder,  f"{self.project_name}_merged.copc.laz")
            stages = [reader('copc', url) for url in s3_urls]
            stages.append(merge())
            stages.append(writer('las', out_file))

        # No Clip and No Merge - download with Boto3
        else:
            download_laz_from_s3(s3_urls, out_folder)

        ## Build PDAL Pipeline and Execute
        pipeline = build_pipeline(stages)
        pipeline.execute()
        
    def build_query(self, bbox_gdf= None, year=None, return_df = False): 

        ## Query Tile Index
        tile_index = self.read_tile_index(bbox_gdf=bbox_gdf)
        within_bounds = len(tile_index) > 0

        if within_bounds:
            if year is not None:
                nearest_year = get_nearest_year(tile_index, year)
                tile_index = tile_index[tile_index.year == str(nearest_year)]

            utm_crs = bbox_gdf.estimate_utm_crs()
            tile_index_local_utm = tile_index.to_crs(utm_crs)

            if return_df:
                return tile_index
            else:
                        ## Reverse Geocode Query
                bbox_gdf_4326 = bbox_gdf.to_crs(4326)
                centroid = bbox_gdf_4326.centroid.iloc[0]
                geolocator = Nominatim(user_agent="canada-lidar")
                location = geolocator.reverse(f"{centroid.y}, {centroid.x}")
                years = [int(x) for x in list(tile_index.year.unique()) if x is not None]
                return  dict(       
                                client_project_name = self.project_name,
                                query_area_m2 = tile_index_local_utm.area.sum(), 
                                query_area_km2 = tile_index_local_utm.area.sum() * 0.000001,
                                years = sorted(years),
                                file_count = len(tile_index),
                                tile_count = len(tile_index.Tile_name.unique()),
                                tile_ids = list(tile_index.Tile_name.unique()),
                                project_names = list(tile_index.Project.unique()),
                                city = location.raw.get('address').get('city'),
                                address = location.address,
                                urls = tile_index.URL.to_list(),
                                bbox = list(bbox_gdf.total_bounds),
                                bbox_wkt = bbox_gdf.to_crs(utm_crs).dissolve().geometry[0].wkt,
                                bbox_area_m2 = bbox_gdf.to_crs(utm_crs).area.sum(),
                                bbox_area_km2 = bbox_gdf.to_crs(utm_crs).area.sum()* 0.000001,
                                bbox_centroid = [centroid.x, centroid.y],
                                crs = str(tile_index.crs),
                                epsg_code = tile_index.crs.to_epsg(),
                                utm_crs = str(utm_crs),
                                providers = list(tile_index.Provider.unique())
                                
                            )
        else:
            return None
        
    
    def query_summary(self, query):
        print('=======================')
        print('QUERY SUMMARY')
        print('=======================')
        print(f'Address: {query["address"]}')
        print(f'Query Area (km2): {query["query_area_km2"].round(2)}')
        print(f'Bounding Box Area: {query["bbox_area_km2"].round(2)}')
        print(f'Number of Tiles: {query["tile_count"]}')
        print(f'LAZ File Count: {query["file_count"]}')
        print(f'Available Years: {query["years"]}')

    def test_polygon(self):
        return gpd.read_file(self.pt.test_poly_fp)
    
    def test_bbox(self):
        return gpd.read_file(self.pt.test_bbox_fp)


    def save_query(self, query):
        
        with open(os.path.join(self.out_folder, f"{self.project_name}_query.json") ,'w' ) as out:
            json.dump(query, out)


def get_nearest_year(tile_index, year):
    ti_years = tile_index.year.dropna().astype(int).unique()
    year_deltas = abs(ti_years - year)
    min_delta = min(year_deltas)
    min_idx = list(year_deltas).index(min_delta)
    return ti_years[min_idx]
