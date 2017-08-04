import pandas as pd
import geojson, json
import os
import numpy as np
import pandas as pd
import datetime as dt

import utils
from utils import db_connect
from src.sat_imagery import gbdx_intersection as sat


'''
Retrieve data on two AOI's over the oceans: marine areas and oceans
For this task, we will first dowload the metadata using the functions
in our module src and from there we will concatenate them and upload
them to postgresql
'''
########################################################################
############################# CAUTION #################################
#######################################################################

# THIS PROCESS TAKE A LOT OF TIME SINCE IS DDOS-ING THE GBDX API. THIS
# MUST BE RUN ONLY ONCE (IF FILES HAVEN'T BEEN DONWLOADED).

#########################################################################
######################### PREPARE IMAGE DATA ############################
#########################################################################
'''
Define AOI's from Carto DB 
marine_areas = url_geojson_to_wkt("https://observatory.carto.com/api/v2/sql?q=select%20*%20from%20observatory.whosonfirst_marinearea")
oceans = sat.url_geojson_to_wkt("https://observatory.carto.com:443/api/v2/sql?q=select%20*%20from%20observatory.whosonfirst_ocean")

aois = list(marine_areas, oceans)
geoms = map(sat.url_geojson_to_wkt, aois)

#Retrieve images for both areas
sat.retrieve_images_marine_areas(aois[1])
sat.retrieve_images_oceans(oceans)
'''
#Read results
results_aois=[]
with open('/mnt/data/shared/gbdx/results_gbdx_marine_areas.txt') as json_file:
    for line in json_file:
        results_aois.append(eval(line))


with open('/mnt/data/shared/gbdx/results_gbdx_ocean_areas.txt') as json_file:
    for line in json_file:
        results_aois.append(eval(line))

#We have retrieve this number of images
print("We have "+ str(len(results_aois)) + " images available in the selected area!")


#Extract properties from images and get a pandas dataframe from it
df_imgs = list(map(lambda x: x["properties"], results_aois))
data_imgs = pd.read_json(json.dumps(df_imgs))

#Explore time of the images
data_imgs["timestamp"] = pd.to_datetime(data_imgs["timestamp"])
data_imgs["date"] = pd.DatetimeIndex(data_imgs["timestamp"]).normalize() #This is not needed, is only to learn how to remove time from timestamps
data_imgs['year'], data_imgs["day"], data_imgs["month"], data_imgs["hour"], data_imgs["minute"], data_imgs["second"] = data_imgs['timestamp'].dt.year, data_imgs["timestamp"].dt.day, data_imgs["timestamp"].dt.month, data_imgs["timestamp"].dt.hour, data_imgs["timestamp"].dt.minute, data_imgs["timestamp"].dt.second
data_imgs = data_imgs.drop_duplicates(subset=['catalogID'], keep = False) 

###############################################################
###################### OPEN POSTGRESQL CONN ###################
###############################################################

engine_output = db_connect.alchemy_connect()
conn_output = engine_output.connect()

###############################################################
###################### UPLOAD DATA AND RUN  ###################
###################### INTERSECTION QUERY #####################
###############################################################

#Upload pandas data.frame to SQL
data_imgs.to_sql('sat_imagery_data', conn_output, schema='gbdx_metadata', if_exists = 'replace', index =False)

#Query (Space and time - 120 secs.)
space_time = '''
CREATE TABLE gbdx_metadata.overlap_marine_ocean_areas AS
SELECT *
FROM ais_messages.full_year_position pts
INNER JOIN gbdx_metadata.sat_imagery_data pol
ON (ST_Intersects(pts.geom, pol."footprintWkt")) AND (@EXTRACT(EPOCH from age(pol.timestamps, pts.timestamp)) < 120);
'''

engine_output.execute(space_time)



