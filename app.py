# -*- coding:utf-8 -*-
import redis, os
from flask import Flask, request, jsonify

GET, POST = "GET", "POST"

redisHost = os.getenv("REDIS_HOST")
redisPort = os.getenv("REDIS_PORT")
redisPwd = os.getenv("REDIS_PASSWORD")
if not redisHost:
	print("get redis host error")
if not redisPort:
	print("get redis port error")
if not redisPwd:
	print("get redis password error")
r = redis.StrictRedis(host=redisHost, port=redisPort, password = redisPwd, db=0)
try:
	test = "test-global"
	r.set(test, "success")
	mark = r.get(test)
	if mark != "success":
		print("set test-global failed")
except Exception as e:
	print("redis connection error:", e)

app = Flask(__name__)

# v1.0
@app.route('/api/v1.0/list', methods=[GET, POST])
def List():
	if request.method == POST:
		postData = request.get_json()
		postData = {"res":postData}
		return jsonify(postData)

@app.route('/api/v1.0/set', methods=[GET, POST])
def Set():
	pass

@app.route('/api/v1.0/add', methods=['GET', 'POST'])
def Add():
	pass

if __name__ == '__main__':
    app.run()