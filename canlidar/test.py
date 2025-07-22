from canlidar import CanadaLIDAR
from canlidar.s3_download import retrieve_tile_index


canl = CanadaLIDAR(project_name = "TEST")







retrieve_tile_index('../data')



print(canl.project_name)