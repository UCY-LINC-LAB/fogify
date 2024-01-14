from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    clientAddr = request.remote_addr
    return render_template('index.html', clientAddr = clientAddr)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)

