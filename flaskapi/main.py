
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

'''
Do as much as we can on the client PC making the middlewear
1. Request with circle. left=0, top=0 becomes left=0 top=page.height-0
| x0,y0      |           |       x1, h-y0 |
|     x1, y1 |   becomes | x0,h-y1        | this is done CLIENT SIDE
but we only need to take each point and flip it, then server side taking mins and maxes automatically works for bbox
2. Respond with contents inside circle. left=0, bottom=0
subtract minx, miny because this is the search box on the SERVER SIDE
|        x1, y1 |         | x0, h-y1        |
| x0, y0        | becomes |        x1, h-y0 | this is done CLIENT SIDE only for rendering
3. Send the search box response (untransformed) to the server to find similar
4. Server responds with found elements
|        x1, y1 |         | x0, h-y1        |
| x0, y0        | becomes |        x1, h-y0 | this is done CLIENT SIDE only for rendering
'''

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

@app.route("/selectinpdf", methods=["POST", "OPTIONS"])
def searchpdf():
  if flask.request.method == "OPTIONS":
    print("Got options from:", flask.request.origin)
    response = build_cors_preflight_response()
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
      selectedPaths, searchRequestData  = pdfsearch.find_shapes_in_drawpaths(pdfFile=pdfFile, drawPaths=drawPaths, pageNumber=pageNumber)
      response = flask.make_response({
        "selectedPaths": selectedPaths,
        "searchRequestData": searchRequestData,
      })
    else:
      response = flask.make_response({
        "error": "pdfFile:{0} drawPaths:{1} pageNumber: {2}".format(bool(pdfFile), bool(drawPaths), bool(pageNumber))
      })
    return build_cors_response(response)
  else:
    print("Unhandled request type:", flask.request.method)

# cd flaskapi && flask --app main.py --debug run
# python3 -m flask --app main.py --debug run
if __name__ == "__main__":
  # For production
  app.run()