import configparser
import requests
import json

LOCAL_URLS = []
REMOTE_URLS = []

def init():
    config = configparser.ConfigParser()
    config.read('central_backend/database.conf')
    LOCAL_URLS.append(config.get('DEFAULT', 'localUSEastURL'))
    REMOTE_URLS.append(config.get('DEFAULT', 'remoteUSEastURL'))
    LOCAL_URLS.append(config.get('DEFAULT', 'localUSWestURL'))
    REMOTE_URLS.append(config.get('DEFAULT', 'remoteUSWestURL'))
    LOCAL_URLS.append(config.get('DEFAULT', 'localCentralURL'))
    REMOTE_URLS.append(config.get('DEFAULT', 'remoteCentralURL'))
    print("Read Backend URLS")


class DBCLient:

    def __init__(self):
        self.url = None
        init()
        with open('./us_state_regions.json', 'r') as f:
            self.region_map = json.load(f)

    def __getURL(self,data):
        state = data.get("state")
        if state:
            region = self.region_map.get(state)
            if region:
                return LOCAL_URLS[region]
        return None

    def addData(self,data):
        try:
            url = self.__getURL(data)
            response = requests.post(f"{url}/addData", json=data)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def fetchUserData(self, user_id,state):
        try:
            url = self.__getURL({"state":state})
            response = requests.get(f"{url}/getUserData", params={"user_id": user_id})
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def fetchPaginatedData(self, page,state, page_size=20):
        try:
            url = self.__getURL({"state":state})
            response = requests.get(f"{url}/getPaginatedData", params={"page": page, "page_size": page_size})
            return response.json()
        except Exception as e:
            return {"error": str(e)}