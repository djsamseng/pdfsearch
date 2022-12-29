
import json

import flask

import pdfsearch

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
  else:
    print("=== Preflight denied ===", flask.request.origin)
  return response

def build_cors_response(response):
  if flask.request.origin in ALLOWED_ORIGINS:
    response.headers.add(ACCESS_CONTROL_ALLOW_ORIGIN, flask.request.origin)
  else:
    print("=== Request denied ===", flask.request.origin)
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
    pdfFile = None
    drawPaths = None
    pageNumber = None
    if "pdfFile" in flask.request.files:
      pdfFile = flask.request.files["pdfFile"]
    if "drawPaths" in flask.request.form:
      drawPaths = json.loads(flask.request.form["drawPaths"])
      drawPaths = [pdfsearch.DrawPath(p) for p in drawPaths]
    if "pageNumber" in flask.request.form:
      pageNumber = int(flask.request.form["pageNumber"])
    if pdfFile is not None and drawPaths is not None and pageNumber is not None:
      searchPaths = pdfsearch.find_shapes_in_drawpaths(pdfFile=pdfFile, drawPaths=drawPaths, pageNumber=pageNumber)
      response = flask.make_response({
        "searchPaths": searchPaths
      })
    else:
      response = flask.make_response({
        "error": "pdfFile:{0} drawPaths:{1} pageNumber: {2}".format(bool(pdfFile), bool(drawPaths), bool(pageNumber))
      })
    return build_cors_response(response)
  else:
    print("Unhandled request type:", flask.request.method)

# cd flaskapi && flask --app main.py --debug run
if __name__ == "__main__":
  # For production
  app.run()