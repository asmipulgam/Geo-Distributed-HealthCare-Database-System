# Script to setup the docker instances all
import subprocess

CMD_OLD = [

"docker network create --driver=bridge --subnet=172.27.0.0/16 --ip-range=172.27.0.0/24 --gateway=172.27.0.1 us-west2-net",
"docker network create --driver=bridge --subnet=172.28.0.0/16 --ip-range=172.28.0.0/24 --gateway=172.28.0.1 us-east4-net",
"docker network create --driver=bridge --subnet=172.29.0.0/16 --ip-range=172.29.0.0/24 --gateway=172.29.0.1 us-central1-net",

"docker network create --driver=bridge --subnet=172.30.0.0/16 --ip-range=172.30.0.0/24 --gateway=172.30.0.1 uswest-useast-net",
"docker network create --driver=bridge --subnet=172.31.0.0/16 --ip-range=172.31.0.0/24 --gateway=172.31.0.1 useast-uscentral-net",
"docker network create --driver=bridge --subnet=172.32.0.0/16 --ip-range=172.32.0.0/24 --gateway=172.32.0.1 uswest-uscentral-net",

"docker run -d --name=roach-seattle-1 --hostname=roach-seattle-1 --ip=172.27.0.11 --cap-add NET_ADMIN --net=us-west2-net --add-host=roach-seattle-1:172.27.0.11 --add-host=roach-seattle-2:172.27.0.12 -p 8080:8080 -v 'roach-seattle-1-data:/cockroach/cockroach-data' cockroachdb/cockroach start --insecure  --locality=region=us-west2,zone=a",
"docker run -d --name=roach-seattle-2 --hostname=roach-seattle-2 --ip=172.27.0.12 --cap-add NET_ADMIN --net=us-west2-net --add-host=roach-seattle-1:172.27.0.11 --add-host=roach-seattle-2:172.27.0.12 -p 8081:8080 -v 'roach-seattle-2-data:/cockroach/cockroach-data' cockroachdb/cockroach start --insecure  --locality=region=us-west2,zone=b",

"docker run -d --name=roach-newyork-1 --hostname=roach-newyork-1 --ip=172.28.0.11 --cap-add NET_ADMIN --net=us-east4-net --add-host=roach-newyork-1:172.28.0.11 --add-host=roach-newyork-2:172.28.0.12 -p 8180:8080 -v 'roach-newyork-1-data:/cockroach/cockroach-data' cockroachdb/cockroach start --insecure  --locality=region=us-east4,zone=a",
"docker run -d --name=roach-newyork-2 --hostname=roach-newyork-2 --ip=172.28.0.12 --cap-add NET_ADMIN --net=us-east4-net --add-host=roach-newyork-1:172.28.0.11 --add-host=roach-newyork-2:172.28.0.12 -p 8181:8080 -v 'roach-newyork-2-data:/cockroach/cockroach-data' cockroachdb/cockroach start --insecure  --locality=region=us-east4,zone=b",

"docker run -d --name=roach-omaha-1 --hostname=roach-omaha-1 --ip=172.29.0.11 --cap-add NET_ADMIN --net=us-central1-net --add-host=roach-omaha-1:172.29.0.11 --add-host=roach-omaha-2:172.29.0.12 -p 8280:8080 -v 'roach-omaha-1-data:/cockroach/cockroach-data' cockroachdb/cockroach start --insecure  --locality=region=us-central1,zone=c",
"docker run -d --name=roach-omaha-2 --hostname=roach-omaha-2 --ip=172.29.0.12 --cap-add NET_ADMIN --net=us-central1-net --add-host=roach-omaha-1:172.29.0.11 --add-host=roach-omaha-2:172.29.0.12 -p 8281:8080 -v 'roach-omaha-2-data:/cockroach/cockroach-data' cockroachdb/cockroach start --insecure  --locality=region=us-central1,zone=f",

"docker exec -it roach-newyork-1 ./cockroach init --insecure",
"docker exec -it roach-seattle-1 ./cockroach init --insecure",
"docker exec -it roach-omaha-1 ./cockroach init --insecure",
"docker exec -it roach-newyork-2 ./cockroach init --insecure",
"docker exec -it roach-seattle-2 ./cockroach init --insecure",
"docker exec -it roach-omaha-2 ./cockroach init --insecure"

]

OLDER = [

     #"docker run -d --name roach-seattle-2  -p 26258:26257 -p 8081:8080 -v roach1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-west1,zone=b",


    #"docker run -d --name roach-newyork-1  -p 26259:26257 -p 8082:8080 -v roach1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-east1,zone=a",


   # "docker run -d --name roach-omaha-2  -p 26262:26257 -p 8085:8080 -v roach1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-central1,zone=f"

    #"docker exec roach-seattle-1 ./cockroach init --insecure",
    #"docker exec roach-newyork-2 ./cockroach init --insecure",
    #"docker exec roach-omaha-1 ./cockroach init --insecure",

]

CMD = [
    "docker run -d --name roach-seattle-1  -p 26257:26257 -p 8080:8080 -v roachs1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-west1,zone=a",

    "docker run -d --name roach-newyork-2  -p 26260:26257 -p 8083:8080 -v roachn2-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-east1,zone=b",

    "docker run -d --name roach-omaha-1  -p 26261:26257 -p 8084:8080 -v roacho1-data:/cockroach/cockroach-data cockroachdb/cockroach start-single-node --insecure --accept-sql-without-tls --locality=region=us-central1,zone=c",



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
    