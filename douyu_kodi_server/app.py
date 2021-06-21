from flask import Flask
from douyu import DouYu
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/room/<room_id>")
def get_room_id(room_id):
    r = DouYu(room_id)
    url = r.get_real_url()
    return url