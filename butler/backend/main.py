from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from utils import send_welcome

load_dotenv()

ENV = os.environ.get("ENV")
if ENV == "PROD":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_PROD")
    mothership_url = os.environ.get("MOTHERSHIP_URL_PROD")
    cluster_name = "prod01awsuswest2"
elif ENV == "DEV":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_DEV")
    mothership_url = os.environ.get("MOTHERSHIP_URL_DEV")
    cluster_name = "dev_cluster"


app = Flask(__name__)
CORS(app)


@app.route("/")
def hello():
    headers = request.headers
    auth = headers.get("Authorization")
    if auth != "Bearer " + mothership_key:
        return jsonify({"message": "ERROR: Unauthorized"}), 401

    return jsonify({"message": "succeed"}), 200


@app.route("/welcome_email", methods=["POST"])
def welcome_email():
    headers = request.headers
    auth = headers.get("Authorization")
    if auth != "Bearer " + mothership_key:
        return jsonify({"message": "ERROR: Unauthorized"}), 401

    data = request.get_json()
    response = send_welcome((data["email"], data["name"]))
    code, body, headers = response.status_code, response.body, response.headers
    print(f"Response code: {code}")
    print(f"Response headers: {headers}")
    print(f"Response body: {body}")
    return jsonify({"message": "Email sent"}), 200


@app.route("/workspace", methods=["POST"])
def workspace():
    headers = request.headers
    auth = headers.get("Authorization")
    if auth != "Bearer " + mothership_key:
        return jsonify({"message": "ERROR: Unauthorized"}), 401

    return 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
