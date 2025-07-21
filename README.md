# CanadaLiDAR - Simple Python API for Canadian LiDAR Data


## Usage


```python
from canlidar import CanadaLIDAR
cnl = CanadaLIDAR(project_name = "YOUR-PROJECT-NAME")
query = cnl.query_bbox(test=True, return_df = False)
```


### Query by Address

```python
query = cnl.query_address(address='University of Waterloo, Ontario, Canada', distance_km = 0.5)
```

### Query by Address

```python
query = cnl.query_city('Toronto', return_df= False)
```

