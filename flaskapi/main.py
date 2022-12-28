
import flask

app = flask.Flask(__name__)

ALLOWED_ORIGINS = set(["http://localhost:3000"])
ALLOWED_HEADERS = ", ".join(["content-type"])
ALLOWED_METHODS = ", ".join(["POST", "OPTIONS"])
ACCESS_CONTROL_ALLOW_ORIGIN = "Access-Control-Allow-Origin"
ACCESS_CONTROL_ALLOW_HEADERS = "Access-Control-Allow-Headers"
ACCESS_CONTROL_ALLOW_METHODS = "Access-Control-Allow-Methods"

def build_cors_preflight_response():
  print("Build for origin:", flask.request.origin)
  response = flask.make_response()
  if flask.request.origin in ALLOWED_ORIGINS:
    response.headers.add(ACCESS_CONTROL_ALLOW_ORIGIN, flask.request.origin)
    response.headers.add(ACCESS_CONTROL_ALLOW_HEADERS, ALLOWED_HEADERS)
    response.headers.add(ACCESS_CONTROL_ALLOW_METHODS, ALLOWED_METHODS)
  return response

def build_cors_response(response):
  if flask.request.origin in ALLOWED_ORIGINS:
    response.headers.add(ACCESS_CONTROL_ALLOW_ORIGIN, flask.request.origin)
  return response

@app.route("/", methods=["GET"])
def default():
  return """
  <div>Flask API</div>
  <div>Send a POST request to /searchpdf</div>
  """

@app.route("/searchpdf", methods=["POST", "OPTIONS"])
def searchpdf():
  if flask.request.method == "OPTIONS":
    response = build_cors_preflight_response()
    print("Got OPTIONS", response)
    return response
  elif flask.request.method == "POST":

    response = flask.make_response({
      "testkey": "testval"
    })
    print("GOT POST:", flask.request)
    return build_cors_response(response)
  else:
    print("Unhandled request type:", flask.request.method)