# PyCanLiDAR - Simple Python API for Canadian LiDAR Data


<div style="text-align: center;">
  <img src="media/coverage_map.png" alt="drawing" width="300">
</div>


The CanLiDAR project is an unofficial pythonic API to query LiDAR point cloud from the [CanElevation Series](https://open.canada.ca/data/en/dataset/7069387e-9986-4297-9f55-0288e9676947) published by the Government of Canada.

LiDAR Data of urban and natural areas are made available as [LAZ Cloud Optimized Point Clouds (COPC) on AWS S3](https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/index.html#pointclouds_nuagespoints/). 

The PyCanLiDAR project allows users run effecient spatial and temporal queries on the point cloud data using convenient query items such as an address, polygon geometries, bounding box coordinates, address, or city name. Point cloud data can also be filtered by year of aquistion. 

All responses are JSON objects containing necessary metadata and URLs for accessing point clouds for their region of interest. JSON was chosen as the standard reponse format to enable simple integrations into web applications. Download functionalities are available with options to clip the point cloud tiles or to download the entire tile.

This projects leverages the COPC streaming capabilities of the [Point Data Abstraction Library (PDAL)](https://pdal.io/en/stable/index.html) to allow for effecient spatial querying and manipulation (clipping to extent) of the point cloud data.


## Getting Started


### Install Dependencies

```bash
git clone https://github.com/medo-younes/py-canlidar
cd py-canlidar
conda create -f environment.yml
```


### Usage

Refer to the Python notebooks for a more hands-on guide: [01_Queries.ipynb](notebooks/01_Queries.ipynb) and [02_Download_.ipynb](notebooks/01_Download.ipynb)


```python
## Import CanadaLIDAR Class and initialize an instance
from canlidar import CanadaLiDAR
cnl = CanadaLIDAR(project_name = "MY-PROJECT")

### Bounding Box Query
bbox = [-75.70643613,  45.42059443, -75.70122192,  45.42389271]
query = cnl.query_bbox(bbox= bbox)

### Address Query
query = cnl.query_address(address='University of Waterloo, Ontario, Canada',distance_km = 0.5)

### City Query
query = cnl.query_city(city = 'Toronto')
cnl.query_summary(query) # Print a summary of your Query
```

### Downloading LAZ Files
```python
cnl.download(  query = query, # A query object 
                root = "../lidar_data", # Root directory for writing LAZ files
                clip = True, # Clips Point clouds according to the polygon passed by the query
                merge_all = True, # Merge point clouds if True, indiviudal LAZ files will be downloaded if False
              )
```


### Map Your Query

Example for Python Notebook.

```python
query = cnl.query_polygon(test=True,return_df= True) # Use the return_df argument to get a GeoDataFrame of the queries tiles
query.explore(column='year')
```
<div>
  <img src="media/query_example.png" alt="drawing" width="400">
</div>



### Query Response Format

All queries return a standard JSON object with the schema shown below. Users can then use the query object to integrate into other applications or to simply download with PyCanLiDAR's downloading functionalities.

You can view a sample of the JSON respoonse [HERE](data/sample.json).

| Key Name | Data Type | Description |
|----------|-----------|-------------|
| query_area_m2 | np.float64 | Total area of the query region in square meters |
| query_area_km2 | np.float64 | Total area of the query region in square kilometers |
| years | list[int] | Years for which LiDAR data is available |
| file_count | int | Number of LiDAR files found for the query |
| tile_count | int | Number of LiDAR tiles covering the query area |
| tile_ids | numpy.ndarray | Array of unique tile identifiers |
| project_names | numpy.ndarray | Array of project names associated with the LiDAR data |
| city | str | City name where the query location is situated |
| address | str | Full address of the query location |
| urls | list[str] | List of URLs to download the LiDAR point cloud files |
| bbox | numpy.ndarray | Bounding box coordinates [min_x, min_y, max_x, max_y] |
| bbox_area_m2 | np.float64 | Area of the bounding box in square meters |
| bbox_area_km2 | np.float64 | Area of the bounding box in square kilometers |
| bbox_centroid | list[float] | Centroid coordinates of bounding box [longitude, latitude] |
| crs | pyproj.CRS | Coordinate Reference System object for the data |
| epsg_code | int | EPSG code identifier for the coordinate system |
| utm_crs | pyproj.CRS | UTM Coordinate Reference System object |
| providers | numpy.ndarray | Array of data providers (e.g., provincial codes) |
