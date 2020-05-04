import os
import pysolr
import requests
import logging
import ctypes



logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def doc_key(dataset_id, file_name):
    return ctypes.c_size_t(hash(f'{dataset_id}{file_name}')).value


class DatasetIngestionHistorySolr:
    _solr_granules = None
    _solr_datasets = None
    _granule_collection_name = "nexusgranules"
    _dataset_collection_name = "nexusdatasets"
    _solr_url = None
    _req_session = None
    _dataset_id = None
    _signature_fun = None
    _latest_ingested_file_update = None

    def __init__(self, solr_url, dataset_id, signature_fun):
        self._solr_url = solr_url
        self._create_collection_if_needed()
        self._solr_granules = pysolr.Solr('/'.join([solr_url.strip('/'), self._granule_collection_name]))
        self._solr_datasets = pysolr.Solr('/'.join([solr_url.strip('/'), self._dataset_collection_name]))
        self._dataset_id = dataset_id
        self._signature_fun = signature_fun
        self._latest_ingested_file_update = self._get_latest_file_update()

    def __del__(self):
        self._push_latest_ingested_date()
        self._req_session.close()

    def push(self, file_path):
        file_path = file_path.strip()
        file_name = os.path.basename(file_path)
        signature = self._signature_fun(file_path)
        self._push_record(file_name, signature)

        if self._latest_ingested_file_update:
            self._latest_ingested_file_update = max(self._latest_ingested_file_update,
                                                    os.path.getmtime(file_path))
        else:
            self._latest_ingested_file_update = os.path.getmtime(file_path)

    def has_valid_cache(self, file_path):
        file_path = file_path.strip()
        file_name = os.path.basename(file_path)
        signature = self._signature_fun(file_path)
        logger.debug(f"compare {signature} with {self._get_signature(file_name)}")
        return signature == self._get_signature(file_name)

    def get_latest_ingested_file_update(self):
        return self._latest_ingested_file_update

    def _push_record(self, file_name, signature):
        hash_id = doc_key(self._dataset_id, file_name)
        self._solr_granules.delete(q=f"id:{hash_id}")
        self._solr_granules.add([{
            'id': hash_id,
            'dataset_s': self._dataset_id,
            'granule_s': file_name,
            'granule_signature_s': signature}])
        self._solr_granules.commit()
        return None

    def _push_latest_ingested_date(self):
        self._solr_datasets.delete(q=f"id:{self._dataset_id}")
        self._solr_datasets.add([{
            'id': self._dataset_id,
            'dataset_s': self._dataset_id,
            'latest_update_l': self._latest_ingested_file_update}])
        self._solr_datasets.commit()

    def _get_latest_file_update(self):
        results = self._solr_datasets.search(q=f"id:{self._dataset_id}")
        if results:
            return results.docs[0]['latest_update_l']
        else:
            return None

    def _get_signature(self, file_name):
        hash_id = doc_key(self._dataset_id, file_name)
        results = self._solr_granules.search(q=f"id:{hash_id}")
        if results:
            return results.docs[0]['granule_signature_s']
        else:
            return None

    def _create_collection_if_needed(self):
        if not self._req_session:
            self._req_session = requests.session()

        payload = {'action': 'CLUSTERSTATUS'}
        result = self._req_session.get('/'.join([self._solr_url.strip('/'), 'admin', 'collections']), params=payload)
        response = result.json()
        node_number = len(response['cluster']['live_nodes'])

        existing_collections = response['cluster']['collections'].keys()

        if self._granule_collection_name not in existing_collections:
            # Create collection
            payload = {'action': 'CREATE',
                       'name': self._granule_collection_name,
                       'numShards': node_number
                       }
            result = self._req_session.get('/'.join([self._solr_url.strip("/"), 'admin', 'collections']), params=payload)
            response = result.json()
            logger.info(f"solr collection created {response}")
        else:
            logger.info(f"collection {self._granule_collection_name} already exists")

        # Update schema
        schema_url = '/'.join([self._solr_url.strip('/'), 'solr', self._granule_collection_name, 'schema'])
        # granule_s # dataset_s so that all the granule of a dataset are less likely to be on the same shard
        # self.add_unique_key_field(schema_url, "uniqueKey_s", "StrField")
        self._add_field(schema_url, "dataset_s", "StrField")
        self._add_field(schema_url, "granule_s", "StrField")
        self._add_field(schema_url, "granule_signature_s", "StrField")

        if self._dataset_collection_name not in existing_collections:
            # Create collection
            payload = {'action': 'CREATE',
                       'name': self._dataset_collection_name,
                       'numShards': node_number
                       }
            result = self._req_session.get('/'.join([self._solr_url.strip('/'), 'admin', 'collections']), params=payload)
            response = result.json()
            logger.info(f"solr collection created {response}")
        else:
            logger.info(f"collection {self._dataset_collection_name} already exists")

        # Update schema
        schema_url = '/'.join([self._solr_url.strip('/'), 'solr', self._dataset_collection_name, 'schema'])
        # granule_s # dataset_s so that all the granule of a dataset are less likely to be on the same shard
        # self.add_unique_key_field(schema_url, "uniqueKey_s", "StrField")
        self._add_field(schema_url, "dataset_s", "StrField")
        self._add_field(schema_url, "latest_update_l", "TrieLongField")

    def _add_field(self, schema_url, field_name, field_type):
        """
        Helper to add a string field in a solr schema
        :param schema_url:
        :param field_name:
        :param field_type
        :return:
        """
        add_field_payload = {
            "add-field": {
                "name": field_name,
                "type": field_type,
                "stored": False
            }
        }
        result = self._req_session.post(schema_url, data=add_field_payload)