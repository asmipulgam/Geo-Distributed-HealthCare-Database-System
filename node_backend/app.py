from flask import Flask, json, request, jsonify
import configparser
import socket
import argparse
import psycopg2

app = Flask(__name__)
REGIONMAP= {
    "central": 5000,
    "east": 5001,
    "west": 5002
}

@app.get("/ping")
def ping():
    return jsonify({"status": "ok", "message": "pong"}), 200


@app.get("/greet")
def greet():
    name = request.args.get("name", "world")
    return jsonify({"greeting": f"Hello, {name}!"}), 200


@app.post("/echo")
def echo():
    # Echo back JSON body or form fields
    status = pingDB()
    return jsonify({"status": status, "region": region}), 200

@app.post("/addData")
def addData():
    data = request.json
    try:
        cursor = dbConnection.cursor()
        insert_query = """
            INSERT INTO health_data (user_id, state, data)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (data['user_id'], data['state'], json.dumps(data['data'])))
        dbConnection.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def pingDB():
    try:
        cursor = dbConnection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        if result and result[0] == 1:
            return True
        else:
            return False
    except Exception as e:
        print(f"Database ping failed: {e}")
        return False

if __name__ == "__main__":
    # Run the Flask development server
    parse = argparse.ArgumentParser(description="Choose Region")
    parse.add_argument("--region", choices=["east", "west", "central"], default="central")
    args = parse.parse_args()
    region = args.region
    confFile = f"node_backend/database.{region}.conf"
    dbConnection = psycopg2.connect(dsn="postgresql://root@localhost:26257/defaultdb?sslmode=disable",connect_timeout=10)
    #print(dbConnection)
    #app.run(host="0.0.0.0", port=5000, debug=True)
