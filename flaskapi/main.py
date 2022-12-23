
from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def default():
  return """
  <div>Flask API</div>
  <div>Send a POST request to /searchpdf</div>
  """

@app.route("/searchpdf", methods=["POST"])
def searchpdf():
  return {
    "testkey": "testval"
  }