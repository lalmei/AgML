import os
import sys
import json
import zipfile
import warnings

import boto3
from tqdm import tqdm

class PublicDataAPI:
    """
    A public API for working with AgML data.

    Attributes
    ----------
    No user specified attributes
    """
    def __init__(self):
        # Read in metadata for data sources file
        self.data_srcs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'assets', 'public_datasources.json')
        with open(self.data_srcs_path) as f:
            self.data_srcs = json.load(f)

        # Define s3 bucket URI
        self.agdata_s3_uri = 'https://s3.us-west-1.amazonaws.com/agdata-data/'

        # Initialize attribute for storing dataset download path
        self.dataset_download_path = None

    @property
    def data_sources(self):
        """Returns a list of AgML public data sources."""
        return list(self.data_srcs.keys())

    def upload_dataset(self, dataset_name, dataset_dir):
        """
        Uploads dataset to agdata-data s3 file storage.
        
        Parameters
        ----------
        dataset_name : str
            name of dataset (without '.zip') -- for list of datasets run self.data_srcs.keys()
        dataset_dir : str
            path to directory where dataset is stored
        """
        # Establish connection with s3 via boto
        self.s3 = boto3.client('s3')

        # Setup progress bar
        self.pg = tqdm(
            total=os.stat(os.path.join(dataset_dir, dataset_name + '.zip')).st_size,
            file = sys.stdout, desc = f"Uploading {dataset_name}")

        # Upload data to agdata-data bucket
        try:
            with open(os.path.join(dataset_dir, dataset_name + '.zip'), 'rb') as data:
                self.s3.upload_fileobj(Fileobj=data, 
                                       Bucket='agdata-data',
                                       Key=dataset_name + '.zip',
                                       Callback=lambda x: self.pg.update(x))
        except:
            warnings.warn(
                f'Upload of {dataset_name} unsuccessful. You may not have permission '
                f'to upload to the agdata-data s3 bucket.', category = UserWarning)

    def download_dataset(self, dataset_name, dest_dir):
        """
        Downloads dataset from agdata-data s3 file storage.
        
        Parameters
        ----------
        dataset_name : str
            name of dataset to download
        dest_dir : str
            path for saving downloaded dataset
        """
        # Establish connection with s3 via boto
        self.s3 = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')

        # Setup progress bar
        self.pg = tqdm(
            total=float(self.s3_resource.ObjectSummary(
                bucket_name='agdata-data', key=dataset_name + '.zip').size),
            file = sys.stdout, desc = f"Downloading {dataset_name}")

        # File path of zipped dataset
        self.dataset_download_path = os.path.join(dest_dir, dataset_name + '.zip')

        # Upload data to agdata-data bucket
        with open(self.dataset_download_path, 'wb') as data:
            self.s3.download_fileobj(Bucket='agdata-data', 
                                     Key=dataset_name + '.zip', 
                                     Fileobj=data,
                                     Callback=lambda x: self.pg.update(x))

        # Unzip downloaded dataset
        with zipfile.ZipFile(self.dataset_download_path, 'r') as z:
            z.printdir()
            print('Extracting files...')
            z.extractall(path=dest_dir)
            print('Done!')

        # Delete zipped file
        os.remove(self.dataset_download_path)
