# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from asyncio import AbstractEventLoop

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import aiohttp
from nexusproto.DataTile_pb2 import *
from tenacity import *

from granule_ingester.writers.MetadataStore import MetadataStore
from granule_ingester.exceptions import SolrFailedHealthCheckError
logger = logging.getLogger(__name__)


class SolrStore(MetadataStore):
    def __init__(self, host_and_port='http://localhost:8983'):
        super().__init__()

        self.TABLE_NAME = "sea_surface_temp"
        self.iso: str = '%Y-%m-%dT%H:%M:%SZ'

        self._host_and_port = host_and_port
        self.geo_precision: int = 3
        self.collection: str = "nexustiles"
        self.log: logging.Logger = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self._session = None

    def connect(self, loop: AbstractEventLoop = None):
        self._session = aiohttp.ClientSession(loop=loop)

    async def health_check(self):
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get('{}/solr/{}/admin/ping'.format(self._host_and_port, self.collection))
                if response.status == 200:
                    return True
                else:
                    logger.error("Solr health check returned status {}.".format(response.status))
        except aiohttp.ClientConnectionError as e:
            raise SolrFailedHealthCheckError("Cannot connect to to Solr!")

        return False

    async def save_metadata(self, nexus_tile: NexusTile) -> None:
        solr_doc = self._build_solr_doc(nexus_tile)

        await self._save_document(self.collection, solr_doc)

    @retry(stop=stop_after_attempt(5))
    async def _save_document(self, collection: str, doc: dict):
        url = '{}/solr/{}/update/json/docs?commit=true'.format(self._host_and_port, collection)
        response = await self._session.post(url, json=doc)
        if response.status < 200 or response.status >= 400:
            raise RuntimeError("Saving data to Solr failed with HTTP status code {}".format(response.status))

    def _build_solr_doc(self, tile: NexusTile) -> Dict:
        summary: TileSummary = tile.summary
        bbox: TileSummary.BBox = summary.bbox
        stats: TileSummary.DataStats = summary.stats

        min_time = datetime.strftime(datetime.utcfromtimestamp(stats.min_time), self.iso)
        max_time = datetime.strftime(datetime.utcfromtimestamp(stats.max_time), self.iso)

        geo = self.determine_geo(bbox)

        granule_file_name: str = Path(summary.granule).name  # get base filename

        tile_type = tile.tile.WhichOneof("tile_type")
        tile_data = getattr(tile.tile, tile_type)

        input_document = {
            'table_s': self.TABLE_NAME,
            'geo': geo,
            'id': summary.tile_id,
            'solr_id_s': '{ds_name}!{tile_id}'.format(ds_name=summary.dataset_name, tile_id=summary.tile_id),
            'sectionSpec_s': summary.section_spec,
            'dataset_s': summary.dataset_name,
            'granule_s': granule_file_name,
            'tile_var_name_s': summary.data_var_name,
            'tile_min_lon': bbox.lon_min,
            'tile_max_lon': bbox.lon_max,
            'tile_min_lat': bbox.lat_min,
            'tile_max_lat': bbox.lat_max,
            'tile_depth': tile_data.depth,
            'tile_min_time_dt': min_time,
            'tile_max_time_dt': max_time,
            'tile_min_val_d': stats.min,
            'tile_max_val_d': stats.max,
            'tile_avg_val_d': stats.mean,
            'tile_count_i': int(stats.count)
        }

        ecco_tile_id = getattr(tile_data, 'tile', None)
        if ecco_tile_id:
            input_document['ecco_tile'] = ecco_tile_id

        for attribute in summary.global_attributes:
            input_document[attribute.getName()] = attribute.getValues(
                0) if attribute.getValuesCount() == 1 else attribute.getValuesList()

        return input_document

    @staticmethod
    def _format_latlon_string(value):
        rounded_value = round(value, 3)
        return '{:.3f}'.format(rounded_value)

    @classmethod
    def determine_geo(cls, bbox: TileSummary.BBox) -> str:
        # Solr cannot index a POLYGON where all corners are the same point or when there are only
        # 2 distinct points (line). Solr is configured for a specific precision so we need to round
        # to that precision before checking equality.
        lat_min_str = cls._format_latlon_string(bbox.lat_min)
        lat_max_str = cls._format_latlon_string(bbox.lat_max)
        lon_min_str = cls._format_latlon_string(bbox.lon_min)
        lon_max_str = cls._format_latlon_string(bbox.lon_max)

        # If lat min = lat max and lon min = lon max, index the 'geo' bounding box as a POINT instead of a POLYGON
        if bbox.lat_min == bbox.lat_max and bbox.lon_min == bbox.lon_max:
            geo = 'POINT({} {})'.format(lon_min_str, lat_min_str)
        # If lat min = lat max but lon min != lon max, or lon min = lon max but lat min != lat max,
        # then we essentially have a line.
        elif bbox.lat_min == bbox.lat_max or bbox.lon_min == bbox.lon_max:
            geo = 'LINESTRING({} {}, {} {})'.format(lon_min_str, lat_min_str, lon_max_str, lat_min_str)
        # All other cases should use POLYGON
        else:
            geo = 'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))'.format(lon_min_str, lat_min_str,
                                                                        lon_max_str, lat_min_str,
                                                                        lon_max_str, lat_max_str,
                                                                        lon_min_str, lat_max_str,
                                                                        lon_min_str, lat_min_str)

        return geo
