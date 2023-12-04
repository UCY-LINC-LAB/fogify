from threading import Thread
from time import sleep

from utils.edge_fuctionality import get_random_metrics, propagate_to_edge

# from utils.weather import Weather
# w = Weather()
# t = w.retrieve_all_raw()
def helping_function():
    data = get_random_metrics()
    for t in data:
        propagate_to_edge(t)

while True:
    sleep(1)
    thread = Thread(target=helping_function)
    thread.start()