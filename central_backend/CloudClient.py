import logging
import requests
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger(__name__)


class CloudClient:
    """Small HTTP client for interacting with a CockroachDB cloud-like REST API.

    This class implements a few convenience methods commonly provided by
    managed database providers' HTTP APIs:
      - list_clusters / get_operational_clusters: enumerate clusters
      - get_cluster: retrieve details for a specific cluster id

    Usage:
      client = CloudClient('https://api.cockroachlabs.cloud', api_key='...')
      clusters = client.list_clusters()
      operational = client.get_operational_clusters()
      details = client.get_cluster('cluster-id')
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 10, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()
        if api_key:
            # Common header approach; some APIs use Authorization: Bearer <key>
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

        # Ensure we accept JSON responses
        self.session.headers.setdefault('Accept', 'application/json')
        self.cluster_details={}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/') }"
        kwargs.setdefault('timeout', self.timeout)
        try:
            resp = self.session.request(method, url, **kwargs)
        except requests.RequestException as e:
            _LOG.debug('HTTP request failed: %s %s %s', method, url, e)
            raise

        content_type = resp.headers.get('Content-Type', '')
        if not resp.ok:
            # Try to include json error message when available
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f'HTTP {resp.status_code} error for {url}: {detail}')

        if 'application/json' in content_type:
            return resp.json()
        return resp.text

    def list_clusters(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Return a list of clusters.

        This method expects the API to return an object containing a list of
        clusters (common keys: `clusters`, `data`, or top-level list). The
        implementation tries several common response shapes and returns a flat
        list of cluster dicts.
        """
        params = params or {}
        data = self._request('GET', '/clusters', params=params)
        #print(data)

        return data

    def get_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """Retrieve details for a specific cluster by id.

        Calls GET /clusters/{cluster_id} and returns the parsed JSON.
        """
        return self._request('GET', f'/clusters/{cluster_id}')

    def get_operational_clusters(self) -> Dict[str, Any]:
        """Return a dict with count and list of operational cluster details.

        Operational is a heuristic: clusters whose `status` field indicates they
        are running/healthy. We treat status values containing one of these
        tokens as operational: 'running', 'healthy', 'ready', 'ok', 'active'.
        """
        clusters = self.list_clusters()
        ok_tokens = {'running', 'healthy', 'ready', 'ok', 'active'}
        operational = []
        for c in clusters:
            status = None
            if isinstance(c, dict):
                # Try common status locations
                status = c.get('status') or c.get('state') or c.get('cluster_status')
            if isinstance(status, str) and any(tok in status.lower() for tok in ok_tokens):
                operational.append(c)

        return {
            'count': len(operational),
            'clusters': operational,
        }
    
    def run_details(self):
        data = self.list_clusters()
        for i in data['clusters']:
            id = i.get('id')
            self.cluster_details[id]={}
            if i.get("name")=='cotton-prawn':
                self.cluster_details[id]["primary_region"] = "central" 
            elif i.get("name")=='sixear-gundi':
                self.cluster_details[id]["primary_region"] = "west"
            else:
                self.cluster_details[id]["primary_region"] = "east"
            self.cluster_details[id]["nodes"] = []
            for r in i.get("regions", []):
                region_name = r.get("name")
                region_id = r.get("sql_dns")
                if region_name == 'us-central1':
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-central1','us-central1a')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-central1','us-central1c')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-central1','us-central1f')
                    })
                elif region_name == 'us-west2':
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-west2','us-west2a')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-west2','us-west2b')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-west2','us-west2c')
                    })
                else:
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-east4','us-east4a')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-east4','us-east4b')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-east4','us-east4c')
                    })
        self.manuallyAddEastNodes()
        print(self.cluster_details)

    def manuallyAddEastNodes(self):
            id="0b7cee76-dc84-441d-9417-b7274fb36cdc"
            primary_region = "us-east4"
            regions = ["us-east4a","us-east4b","us-east4c"]
            for i in range(3):
                region_id = f"{id}.gcp.aws-us-east-1.cockroachlabs.cloud:26257"
                self.cluster_details[id]["nodes"].append({
                    "node_region": primary_region,
                    "node_id": region_id.replace('us-east4',regions[i])
                    })

    def getClusterDetails(self):
        return self.cluster_details
         
        
            


        
if __name__ == "__main__":
    API_KEY = "CCDB1_lvWREcRl7F7gyWRg0UIlH4_7wJiJIeZVhaTLWUOe3rJeoE1T2SUFRU4aMljkxYE"
    client = CloudClient('https://cockroachlabs.cloud/api/v1', api_key=API_KEY)
    client.run_details()