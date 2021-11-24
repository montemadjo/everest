# ovo ovako ne smije da se radi. Ovaj modul treba da se instalira na regularan način.
# na ovaj način se ne može imati konzistentan kod
import requests
import time
from requests.auth import HTTPDigestAuth

class Camera:
    def __init__(self, URL, username, password) -> None:
        self.url = URL
        self.username = username
        self.password = password
        self.raw_high_request = '<IOPortData version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema"><outputState>high</outputState></IOPortData>'
        self.raw_low_request = '<IOPortData version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema"><outputState>low</outputState></IOPortData>'

    def postOutputRequest(self, state) -> None:
        if state is 1:
            response = requests.put(self.url, data=self.raw_high_request, auth=HTTPDigestAuth(self.username, self.password))
            print(response)
        elif state is 0:
            response = requests.put(self.url, data=self.raw_low_request, auth=HTTPDigestAuth(self.username, self.password))
            print(response)
        
    def switchOutput(self, interval) -> None:
        self.postOutputRequest(1)
        time.sleep(interval)
        self.postOutputRequest(0)