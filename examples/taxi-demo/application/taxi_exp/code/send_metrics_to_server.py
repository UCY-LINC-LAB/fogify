from utils.edge_fuctionality import propagate
import os
if os.path.exists("/data_edge"):
    myFile = open("/data_edge", 'r')

    propagate(data=myFile.readlines())

    myFile.close()
    os.remove("/data_edge")
else:
    print("There is no data")