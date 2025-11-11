# Script to setup the docker instances all
import subprocess

CMD = [
#     "docker run -d --name roach-seattle-1  -p 26257:26257 -p 8080:8080 -v roachs1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-west1,zone=a",

#     "docker run -d --name roach-newyork-2  -p 26260:26257 -p 8083:8080 -v roachn2-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-east1,zone=b",

#     "docker run -d --name roach-omaha-1  -p 26261:26257 -p 8084:8080 -v roacho1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-central1,zone=c",

    "docker run -d --name roach-seattle-1 --hostname roach-seattle-1 --net crdb-net -p 26257:26257 -p 8080:8080 -v roachs1-data:/cockroach/cockroach-data cockroachdb/cockroach start --insecure --accept-sql-without-tls --listen-addr=0.0.0.0:26257 --http-addr=0.0.0.0:8080 --advertise-addr=roach-seattle-1:26257 --locality=region=us-west1,zone=a --join=roach-seattle-1:26257,roach-newyork-2:26257,roach-omaha-1:26257",

    "docker run -d --name roach-newyork-2 --hostname roach-newyork-2 --net crdb-net -p 26260:26257 -p 8083:8080 -v roachn2-data:/cockroach/cockroach-data cockroachdb/cockroach start --insecure --accept-sql-without-tls --listen-addr=0.0.0.0:26257 --http-addr=0.0.0.0:8080 --advertise-addr=roach-newyork-2:26257 --locality=region=us-east1,zone=b --join=roach-seattle-1:26257,roach-newyork-2:26257,roach-omaha-1:26257",

    "docker run -d --name roach-omaha-1 --hostname roach-omaha-1 --net crdb-net -p 26261:26257 -p 8084:8080 -v roacho1-data:/cockroach/cockroach-data cockroachdb/cockroach start --insecure --accept-sql-without-tls --listen-addr=0.0.0.0:26257 --http-addr=0.0.0.0:8080 --advertise-addr=roach-omaha-1:26257 --locality=region=us-central1,zone=c --join=roach-seattle-1:26257,roach-newyork-2:26257,roach-omaha-1:26257",

    "docker exec -it roach-seattle-1 cockroach init --insecure --host=roach-seattle-1:26257",

    "docker exec -it roach-seattle-1 cockroach sql --insecure --execute=\" \
CREATE TABLE IF NOT EXISTS patients ( \
  \"id\" INT PRIMARY KEY, \
  \"first_name\" STRING, \
  \"last_name\" STRING, \
  \"email\" STRING, \
  \"Region\" STRING NOT NULL, \
  \"updated_at\" TIMESTAMP DEFAULT now() \
); \
ALTER TABLE patients \
PARTITION BY LIST (\"Region\") ( \
  PARTITION p_seattle VALUES IN ('us-west1'), \
  PARTITION p_omaha   VALUES IN ('us-central1') \
); \
ALTER PARTITION p_seattle OF TABLE patients CONFIGURE ZONE USING \
  num_replicas = 2, \
  constraints = '{\"+region=us-west1\": 1, \"+region=us-east1\": 1}', \
  voter_constraints = '{\"+region=us-west1\": 1, \"+region=us-east1\": 1}', \
  lease_preferences = '[[+region=us-west1]]'; \
ALTER PARTITION p_omaha OF TABLE patients CONFIGURE ZONE USING \
  num_replicas = 2, \
  constraints = '{\"+region=us-central1\": 1, \"+region=us-east1\": 1}', \
  voter_constraints = '{\"+region=us-central1\": 1, \"+region=us-east1\": 1}', \
  lease_preferences = '[[+region=us-central1]]'; \
\"" ,


    "docker exec roach-seattle-1 ./cockroach sql --insecure --execute=\"CREATE DATABASE IF NOT EXISTS west;\"",
    "docker exec roach-newyork-2 ./cockroach sql --insecure --execute=\"CREATE DATABASE IF NOT EXISTS central;\"",
    "docker exec roach-newyork-2 ./cockroach sql --insecure --execute=\"CREATE DATABASE IF NOT EXISTS west;\"",
    "docker exec roach-omaha-1 ./cockroach sql --insecure --execute=\"CREATE DATABASE IF NOT EXISTS central;\"",
    "docker exec roach-seattle-1 ./cockroach sql --insecure --execute=\"USE west;\"",
    "docker exec roach-omaha-1 ./cockroach sql --insecure --execute=\"USE central;\"",
    # Apply west schema using a schema file to avoid shell-quoting errors
    "docker exec -i roach-seattle-1 cockroach sql --insecure < ./schemas/schema_west.sql",
    "docker exec -i roach-newyork-2 cockroach sql --insecure < ./schemas/schema_west.sql",
    "docker exec -i roach-omaha-1 cockroach sql --insecure < ./schemas/schema_central.sql",
    "docker exec -i roach-newyork-2 cockroach sql --insecure < ./schemas/schema_central.sql",


]

if __name__ == "__main__":
    for cmd in CMD:
        subprocess.run(cmd, shell=True, check=True)
    