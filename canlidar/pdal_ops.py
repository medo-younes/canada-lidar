import json
import pdal 




def reader(reader_type, filename, polygon=None):

    stage = {
            "type" : f"readers.{reader_type}", 
            "filename" : filename,   
        }
    if polygon is not None: stage.update(dict(polygon = polygon))
    return stage

def writer(writer_type, filename):

    return {
        "type" : f"writers.{writer_type}", 
        "filename" : filename,
        }
 


def merge():
    return {"type": "filters.merge"}
def build_pipeline(stages):

    pipeline_dict = dict(pipeline=stages)
    pipeline_json = json.dumps(pipeline_dict)
    return pdal.Pipeline(pipeline_json)
     
