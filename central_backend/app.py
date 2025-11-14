import configparser
import os
import requests
from flask import Flask, request, jsonify
from client import DBClient

# URL of the node backend to forward paginated queries to
NODE_BACKEND_URL = os.environ.get("NODE_BACKEND_URL", "http://localhost:5001")

app = Flask(__name__)


# Simple CORS handling so frontend (vite) can call this API during development.
# For production, use flask-cors or restrict origins appropriately.
@app.before_request
def _handle_options():
    # Respond to preflight OPTIONS requests
    if request.method == "OPTIONS":
        resp = app.make_response(("", 200))
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        resp.headers[
            "Access-Control-Allow-Headers"
        ] = request.headers.get("Access-Control-Request-Headers", "*")
        return resp


@app.after_request
def _add_cors_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    response.headers.setdefault(
        "Access-Control-Allow-Headers", "Content-Type,Authorization,Accept,Origin"
    )
    return response




@app.get("/ping")
def ping():
    return jsonify({"status": "ok", "message": "pong"}), 200


@app.get("/greet")
def greet():
    name = request.args.get("name", "world")
    return jsonify({"greeting": f"Hello, {name}!"}), 200

@app.post("/addData")
def addData():
    # Echo back JSON body or form fields
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict(flat=True)
    
    return jsonify({"received": data}), 200


@app.post("/echo")
def echo():
    # Echo back JSON body or form fields
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict(flat=True)
    return jsonify({"received": data}), 200


@app.get("/api/all")
def proxy_api_all():
    """Forward paginated query requests from frontend to the node backend.

    Query params forwarded: region, cursor, dir, page_size
    """
    params = {k: v for k, v in request.args.items()}
    try:
        resp = requests.get(f"{NODE_BACKEND_URL}/api/all", params=params, timeout=10)
    except Exception as e:
        return jsonify({"error": f"failed to contact node backend: {e}"}), 502

    try:
        data = resp.json()
    except Exception:
        return jsonify({"error": "node backend returned non-json response"}), 502

    return jsonify(data), resp.status_code


if __name__ == "__main__":
    # Run the Flask development server
    app.run(host="0.0.0.0", port=5010, debug=True)
    db = DBClient()
    db.init()
    print("Client initialized")
