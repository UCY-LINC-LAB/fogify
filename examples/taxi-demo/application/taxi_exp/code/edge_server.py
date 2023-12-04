import datetime

from flask import Flask, request
from utils.edge_fuctionality import propagate

app = Flask(__name__)

@app.route("/", methods=['POST'])
def save():
    myFile = open("/data_edge", 'a+')
    myFile.write(str(request.data))
    myFile.close()
    return "{'success':'true'}"

@app.route("/test/<timestamp>", methods=['GET'])
def testing(timestamp):
    return str(datetime.datetime.now().timestamp() - float(timestamp))

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)