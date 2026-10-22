import requests  # Now we can send HTTP requests
from config import HUB_URL  # Gets Hub address from main_pc/config.py


def check_hub_health():
    try:
        # send a GET request to the /health endpoint of the Hub
        response = requests.get(HUB_URL + "/health", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "offline", "hub_name": None}
    except requests.RequestException:
        return {"status": "offline", "hub_name": None}


def get_hub_info():
    try:
        response = requests.get(HUB_URL + "/hub-info", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return {"hub_name": None, "hub_version": None}
    except requests.RequestException:
        return {"hub_name": None, "hub_version": None}


def get_resources():
    try:
        response = requests.get(HUB_URL + "/resources", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None


def get_expedition():
    try:
        response = requests.get(HUB_URL + "/expedition", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    except requests.RequestException:
        return None


def get_infrastructure():
    try:
        response = requests.get(HUB_URL + "/infrastructure", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None


def get_engineering():
    try:
        response = requests.get(HUB_URL + "/engineering", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None


def dispatch_expedition(location):
    try:
        response = requests.post(
            HUB_URL + "/expedition/dispatch", json={"location": location}, timeout=2
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None


def request_generator_repair():
    try:
        response = requests.post(HUB_URL + "/engineering/repair", timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None


def advance_cycle(action):
    try:
        response = requests.post(
            HUB_URL + "/advance-cycle", json={"action": action}, timeout=2
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None
