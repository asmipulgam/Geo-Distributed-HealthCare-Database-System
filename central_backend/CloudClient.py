import requests
from typing import Any, Dict, List, Optional


# Based on the classroom discussion for a UI similar to Local cluster Admin UI, We 
# are interfacing with cloud cockroachDB API to get the cluster details like region and node information
# This is limited due to restricted support on free tier.
# More details and controls can be done if production ready dedicated clusters is used on cockroachDB (PAID/Enterprise Hosting)
class CloudClient:
    def __init__(self, base_url: str = "https://cockroachlabs.cloud/api/v1", api_key: Optional[str] = None, timeout: int = 10, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

        self.session.headers.setdefault('Accept', 'application/json')
        self.cluster_details={}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/') }"
        kwargs.setdefault('timeout', self.timeout)
        try:
            resp = self.session.request(method, url, **kwargs)
        except requests.RequestException as e:
            print("Error connecting to CDB API:", e)
            raise

        content_type = resp.headers.get('Content-Type', '')
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f'HTTP {resp.status_code} error for {url}: {detail}')

        if 'application/json' in content_type:
            return resp.json()
        return resp.text

    def list_clusters(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        data = self._request('GET', '/clusters', params=params)

        return data

    def get_cluster(self, cluster_id: str) -> Dict[str, Any]:
        return self._request('GET', f'/clusters/{cluster_id}')

    def get_operational_clusters(self) -> Dict[str, Any]:
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
            if i.get("name")=='uscentral':
                self.cluster_details[id]["primary_region"] = "central" 
            elif i.get("name")=='uswest':
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
                    "node_id": region_id.replace('us-east1','us-east1a')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-east1','us-east1b')
                    })
                    self.cluster_details[id]["nodes"].append({
                    "node_region": region_name,
                    "node_id": region_id.replace('us-east1','us-east1c')
                    })

    def getClusterDetails(self):
        return self.cluster_details
         
        
            


        
if __name__ == "__main__":
    API_KEY = "CCDB1_lvWREcRl7F7gyWRg0UIlH4_7wJiJIeZVhaTLWUOe3rJeoE1T2SUFRU4aMljkxYE"
    client = CloudClient('https://cockroachlabs.cloud/api/v1', api_key=API_KEY)
    client.run_details()