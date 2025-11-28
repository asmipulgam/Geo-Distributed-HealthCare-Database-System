import psycopg2
import configparser
import time

#Created this to manually take backup and upload to GCS
#Unfortunately for CokckroachDB Free tier, Backup is automated and stored on their own server with no user control
# Hence unable to implement this feature effectively
class Backup:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.gcs_bucket = self.readGCSPath()
        self.gcs_key = self.readGCSKey()

        print(f"Initialized Backup with GCS bucket: {self.gcs_bucket} and GCS key: {self.gcs_key}")

    def readGCSKey(self):
        with open('gcpkey.b64', 'r') as f:
            return f.read()


    def readGCSPath(self):
        config = configparser.ConfigParser()
        config.read('database.conf',encoding='utf-8')
        bucket = config.get('DEFAULT', 'GOOGLE_CLOUD_STORAGE_BUCKET')
        bucket = bucket.removeprefix('"')
        bucket = bucket.removesuffix('"')
        return bucket

    def __getBackupPath(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.gcs_bucket}/backups/backup_{timestamp}?AUTH=specified&CREDENTIALS={self.gcs_key}"
        return backup_path
        

    def create_backup(self, region) -> None:
        backup_name = self.__getBackupPath()
        with psycopg2.connect(self.dsn) as conn:
           with conn.cursor() as cur:
               cur.execute(f"BACKUP DATABASE {region} INTO '{backup_name}' AS OF SYSTEM TIME '-10s' WITH DETACHED;")
        conn.close()

    def restore_backup(self, backup_name: str) -> None:
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(f"RESTORE FROM '{backup_name}';")
        conn.close()

if __name__ == "__main__":
    dsn = "postgresql://root@localhost:26257/west?sslmode=disable"
    backup_manager = Backup(dsn)
    backup_manager.create_backup("west")