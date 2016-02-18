# This file is part of Open Austin's Data Portal Analysis project.
# For more information see README.md in the project's root directory.

import requests
import logging
import datetime
import json

logging.getLogger()

class SocIdGetter(object):
    """class SocIdGetter()
    Fetches a collection of views from data.austintexas.gov, and populates a collection
    of view id's and types
    """
    def __init__(self, views_url, migrations_url):
        """Initializes a Socrata Id Getter.
        Retrieves view metadata from Socrata, and filters / retrieves tabular data
        for each view.
        """
        self._views_url = views_url
        self._migrations_api = migrations_url


    def _download_views(self):
        """This function downloads views.json in chunks and informs the user of
        progress every 100 chunks."""
        localfile = 'views.json'
        req = requests.get(self._views_url, stream=True)
        chunknum = 0
        logging.info("Downloading {0}".format(self._views_url))
        with open(localfile, 'wb') as local_f:
            for chunk in req.iter_content(chunk_size=1024):
                if chunk:
                    if(chunknum % 100 == 0):
                        logging.info("Got chunk {0} of {1}.".format(chunknum, localfile))
                    local_f.write(chunk)
                    chunknum += 1
            logging.info("views.json was downloaded in {0} chunks".format(chunknum))
        with open(localfile) as view_json:
            json_str = view_json.read()
            views_dict = json.loads(json_str)
        return views_dict


    def get_ids(self):
        """Fetches views from Socrata, returns a collection of view metadata."""
        views_dict = self._download_views()
        view_metadata = []
        for view in views_dict['results']:
            try:
                display_type = view['view']['displayType']
            except(KeyError):
                # this means the the view represents a data_lens page,
                # so we ignore it
                continue
            soc_id = view['view']['id']
            view_type = view['view']['viewType']
            display_type = view['view']['displayType']
            item = [soc_id, view_type, display_type]
            # these attributes are used later on
            # to filter out stuff we don't want
            view_metadata.append(item)

        tabular_ids = self.filter_view_ids(view_metadata)
        fourby_list = self.filter_tabular_ids(tabular_ids)
        return fourby_list

    @staticmethod
    def filter_view_ids(view_metadata):
        """Retrieves tabular data ids from the set of Socrata views."""
        tabular_ids = []
        for item in view_metadata:
            if item[1] == "tabular":
                if item[2] == "table":
                    tabular_ids.append(item[0])
                else:
                    continue
            else:
                continue
        return tabular_ids

    def filter_tabular_ids(self, tabular_ids):
        """For each set of tabular data, fetch updated id from Socrata's
        migrations api.
        """
        fourby_list = []
        # these will be the "new back end" ids of primary data assets
        for tab_id in tabular_ids:
            url = self._migrations_api + tab_id
            req = requests.get(url)
            response_json = req.json()
            try:
                fourby_item = response_json['nbeId']
            except(KeyError):
                logging.info("{0} is not a primary data asset.".format(tab_id))
                continue
            else:
                fourby_list.append(fourby_item)
        return fourby_list


class ViewRequestHandler(object):
    """class ViewRequestHandler()
    Fetches view data given a Socrata id.
    """
    def __init__(self, view_api_url):
        """Initializes view request url."""
        self._request_url = view_api_url

    def get_view(self, socrata_id):
        """Fetches view data for a given socrata_id."""
        request_url = self._request_url + socrata_id + '.json'
        result = requests.get(request_url)
        if result.status_code is 404:
            logging.critical("404 response from {0}".format(request_url))
            return "null"
        if 'error' in result.json().keys():
            logging.critical("Error getting data from {0} message: {1}".format(request_url, result.json()['message']))
            return "null"
        logging.info("Got data from {0}".format(request_url))

        dataset = result.json()
        cur_time = datetime.datetime.now().replace(microsecond=0)
        dataset['snapshot_date_time'] = cur_time.isoformat()

        return dataset
