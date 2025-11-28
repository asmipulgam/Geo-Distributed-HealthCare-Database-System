from google.cloud import storage
from google.oauth2 import service_account
import configparser
import re
from datetime import datetime, timedelta

# We initally created this class when working with docker for the below reason:
# CockroachDB has inbuilt functionality support to push backups to either local filesystem or S3-compatible storages like AWS S3, 
# Google Cloud Storage, etc. So we planned to manually take backups regularly and push to GCS periodically
# in the admin section of the frontend, Display the list of backups with timestamp based on the timestamped folder in 
# google cloud storage. As we moved to CockroachDB, we do not have support for this functionality and hence not used.
# but have preserved the code, which was verified on Local Docker instances.
class GCSClient:

    def __readGCSConfig(self):
        config = configparser.ConfigParser()
        config.read('database.conf',encoding='utf-8')
        bucket = config.get('DEFAULT', 'GOOGLE_CLOUD_STORAGE_BUCKET')
        bucket = bucket.removeprefix('"gs://')
        bucket = bucket.removesuffix('"')
        return bucket

    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file('gcpkey.json')
        self.client = storage.Client(credentials=self.creds)
        self.bucket_name = self.__readGCSConfig()
        print(f"GCS Bucket Name: {self.bucket_name}")
        self.bucket = self.client.get_bucket(self.bucket_name)
        print(f"Initialized GCS Client with bucket: {self.bucket_name}/backups/")
        
    def get_backups(self):
        prefix = 'backups'
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        parents = set()
        for blob in blobs:
            name = blob.name or ''
            if name.startswith(prefix + '/'):
                rest = name[len(prefix) + 1:]
            else:
                rest = name
            first = rest.split('/', 1)[0] if rest else ''
            if first:
                parents.add(first)

        return sorted(parents)

    def _find_representative_blob(self, backup_name: str):
        prefixes = [f'backups/{backup_name}/metadata/latest/', f'backups/{backup_name}/']
        for p in prefixes:
            blobs = list(self.client.list_blobs(self.bucket_name, prefix=p, max_results=5))
            if blobs:
                return blobs[0]
        return None

    def get_readable_backup_files(self, expiration_seconds: int = 3600):
        results = []
        backups = self.get_backups()
        for b in backups:
            ts_str = None
            url = None

            m = re.match(r'^backup_(\d{8})_(\d{6})$', b)
            if m:
                date_part, time_part = m.group(1), m.group(2)
                try:
                    dt = datetime.strptime(date_part + time_part, '%Y%m%d%H%M%S')
                    ts_str = dt.strftime('%d/%m/%Y %H:%M:%S')
                except Exception:
                    ts_str = None

            # Find a representative blob to generate a signed URL
            try:
                blob = self._find_representative_blob(b)
                if blob is not None:
                    blob_obj = self.bucket.blob(blob.name)
                    try:
                        url = blob_obj.generate_signed_url(expiration=timedelta(seconds=expiration_seconds))
                    except Exception:
                        try:
                            url = blob_obj.generate_signed_url(expiration=expiration_seconds)
                        except Exception:
                            url = None
            except Exception:
                url = None

            results.append({'name': b, 'timestamp': ts_str, 'download_url': url})

        return results
    
    def getReadableBackupFiles(self):
        return self.get_readable_backup_files()

if __name__ == "__main__":
    gcs_client = GCSClient()
    backups = gcs_client.getReadableBackupFiles()
    print("Available backups in GCS:")
    for b in backups:
        print(f"- {b['name']} | {b.get('timestamp')} | {b.get('download_url')}")
