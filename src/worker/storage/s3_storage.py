import os

from boto.s3.key import Key
from boto.s3.connection import S3Connection


class S3Storage():
    BUCKET = 'klee-output'

    def __init__(self, access_key=None, secret_key=None):
        s3_access_key = access_key or os.environ['AWS_ACCESS_KEY']
        s3_secret_key = secret_key or os.environ['AWS_SECRET_KEY']

        self.conn = S3Connection(s3_access_key, s3_secret_key)
        # Make sure our S3 bucket exists.
        # Buckets are like domain names. Must be unique accross S3!
        self.conn.create_bucket(S3Storage.BUCKET)

    def store_file(self, file_path):
        bucket = self.conn.get_bucket(S3Storage.BUCKET)

        k = Key(bucket)
        k.key = os.path.basename(file_path)
        k.set_contents_from_filename(file_path)
        k.set_acl('public-read')

        return k.generate_url(expires_in=0, query_auth=False)
