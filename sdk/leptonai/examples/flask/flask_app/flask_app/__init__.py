import flask

app = flask.Flask(__name__)


@app.get("/")
def hello():
    return "Hello from Flask!"
