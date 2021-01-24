from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=['POST'])
def save():
    myFile = open("data", 'a+')
    myFile.write(str(request.data))
    myFile.close()
    return "{'success':'true'}"

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)