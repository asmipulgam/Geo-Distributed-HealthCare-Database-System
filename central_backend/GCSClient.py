from google.cloud import storage
from google.oauth2 import service_account
import configparser
import re
from datetime import datetime, timedelta

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
        """Return a sorted list of unique immediate subfolders under `backups/`.

        Example: for blob names like:
          backups/backup_20251115_141431/metadata/latest/LATEST-...
          backups/backup_20251115_141431/2025/11/.../BACKUP-CHECKPOINT-...

        This will return: ['backup_20251115_141431']
        """
        prefix = 'backups'
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        parents = set()
        for blob in blobs:
            name = blob.name or ''
            # strip the prefix + a possible leading slash
            if name.startswith(prefix + '/'):
                rest = name[len(prefix) + 1:]
            else:
                rest = name
            # first path segment is the immediate parent folder under backups
            first = rest.split('/', 1)[0] if rest else ''
            if first:
                parents.add(first)

        return sorted(parents)

    def _find_representative_blob(self, backup_name: str):
        """Return a Blob object that can be used as a downloadable representative
        for the given backup folder. Preference order:
          1. backups/{backup_name}/metadata/latest/* (first match)
          2. the first blob under backups/{backup_name}/
        Returns None if no blob found.
        """
        # Prefer metadata/latest
        prefixes = [f'backups/{backup_name}/metadata/latest/', f'backups/{backup_name}/']
        for p in prefixes:
            blobs = list(self.client.list_blobs(self.bucket_name, prefix=p, max_results=5))
            if blobs:
                # return the first blob object (list_blobs yields Blob-like objects)
                return blobs[0]
        return None

    def get_readable_backup_files(self, expiration_seconds: int = 3600):
        """Return a list of dicts for each backup with readable timestamp and a signed download URL.

        Each dict contains: {
          'name': <backup folder name>,
          'timestamp': 'dd/mm/yyyy hh:mm:ss' | None,
          'download_url': <signed url> | None
        }

        The method calls `get_backups()` to obtain folder names.
        """
        results = []
        backups = self.get_backups()
        for b in backups:
            ts_str = None
            url = None

            # Parse timestamp from expected pattern: backup_YYYYMMDD_HHMMSS
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
                    # Ensure we have a Blob object bound to our bucket instance
                    blob_obj = self.bucket.blob(blob.name)
                    # generate_signed_url accepts datetime.timedelta for expiration
                    try:
                        url = blob_obj.generate_signed_url(expiration=timedelta(seconds=expiration_seconds))
                    except Exception:
                        # Fallback: try numeric seconds (older clients)
                        try:
                            url = blob_obj.generate_signed_url(expiration=expiration_seconds)
                        except Exception:
                            url = None
            except Exception:
                url = None

            results.append({'name': b, 'timestamp': ts_str, 'download_url': url})

        return results
    
    def getReadableBackupFiles(self):

        """Compatibility wrapper exposing camelCase method name used elsewhere.
        Returns the same structure as `get_readable_backup_files`.
        """
        return self.get_readable_backup_files()

if __name__ == "__main__":
    gcs_client = GCSClient()
    backups = gcs_client.getReadableBackupFiles()
    print("Available backups in GCS:")
    for b in backups:
        print(f"- {b['name']} | {b.get('timestamp')} | {b.get('download_url')}")
