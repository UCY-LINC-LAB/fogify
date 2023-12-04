import datetime

import requests
import sys
if __name__ == '__main__':
    ip = sys.argv[1]
    timestamp = datetime.datetime.now().timestamp()
    print(requests.get("http://%s:8000/test/%s"%(ip, timestamp)).text)