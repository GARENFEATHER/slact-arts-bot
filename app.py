from flask import Flask, request, jsonify
import requests, os, re

# Project Data
GET, POST = "GET", "POST"
projectKey = os.getenv("PROJECT_KEY")
if not projectKey:
	raise Exception('no project key detected!')
projectLatest = projectKey + "-latest"
projectTotal = projectKey + "-total"
patternListAll = "^<@.+> list all$"
patternListOne = "^<@.+> list <@(.+)>$"
patternLatest = "^<@.+> latest$"
patternAdd = "^<@.+> add (http[s]*://.+,)+$"
patternDel = "^<@.+> delete (http[s]*://.+,)$"
patternSetTarget = "^<@.+> set target ([0-9]+)$"
patternGetTarget = "^<@.+> get target$"
patternRandom = "^<@.+> give me ([1-9])!*$"

# Redis Connection
redisHost = os.getenv("REDIS_HOST")
redisPort = os.getenv("REDIS_PORT")
redisPwd = os.getenv("REDIS_PASSWORD")
if not redisHost:
	raise Exception("get redis host error")
if not redisPort:
	raise Exception("get redis port error")
if not redisPwd:
	raise Exception("get redis password error")
r = redis.StrictRedis(host=redisHost, port=redisPort, password = redisPwd, db=0)
try:
	test = "test-global"
	r.set(test, "success")
	mark = r.get(test)
	if mark != "success":
		raise Exception("set test-global failed")
except Exception as e:
	print("redis connection error:", e)

# Process Method
def ArtsList(queryType, query):
	if queryType == "rand":
		totalGet, respStr = set(), "rand arts recommended for you:\n"
		total = r.scard(projectTotal)
		if total < query * 2:
			query = total
			respStr = "total added:" + total + "\n" + respStr
		while len(totalGet) < query:
			url = r.srandmember(projectTotal)
			totalGet.add(url)# TODO: dead lock possible
		for i in range(len(totalGet)):
			respStr += string(i) + ": " + url + "\n"
		return respStr
	elif queryType == "latest":
		latest = r.lrange(projectLatest, query * -1, -1)
		if len(latest) == 0:
			return "sorry... no latest arts list now"
		else:
			respStr = "latest added arts here:\n"
			for i in range(len(latest)):
				respStr += string(i) + ": " + latest[i] + "\n"
			return respStr
	elif queryType == "user":
		userArts = r.smembers(projectKey + "-" + query)
		if len(userArts) != 0:
			respStr = "arts you've added:\n"
			for arts in respStr:
				respStr += arts + "\n"
			return respStr
		else:
			return "you've never added your arts, add one now!"

def TargetSet(user, value):
	result = r.set(projectKey + "-" + user + "-target", value)
	if result:
		return "target successfully set, new target:" + string(value)
	else:
		return "target set failed...sorry, please check again"

def StatusGet(user):
	targetBefore = r.get(projectKey + "-" + user + "-target")
	addedCount = r.scard(projectKey + "-" + user)
	if not targetBefore:
		return "no target now...let's set one!" + "\nyou've added:" + string(addedCount)
	else:
		return "your target:" + string(targetBefore) + "\nyou've added:" + string(addedCount)

def ArtsAdd(listToAdd):
	totalAdded = 0
	for url in listToAdd:
		count = r.sadd(projectTotal, url)
		if count != 0:
			totalAdded += 1
			r.sadd(projectKey + "-" + user, url)
			r.rpush(projectLatest, url)
			count = r.llen(projectLatest)
			if count > 100:
				r.lpop(projectLatest)
	if totalAdded == 0:
		return "nothing has benn added ..."
	elif totalAdded == 1:
		return "congratulations! 1 post has been added!"
	else:
		return "congratulations! " + string(totalAdded) + " posts have been added!"

def ArtsDel(listToDelete):
	totalDeleted = 0
	for url in listToDelete:
		count = r.srem(projectTotal, url)
		if count != 0:
			totalDeleted += 1
			r.srem(projectKey + "-" + user, url)
			r.lrem(projectLatest, 0, url)
	if totalDeleted == 0:
		return "nothing has benn deleted ..."
	elif totalDeleted == 1:
		return "congratulations! 1 post has been deleted!"
	else:
		return "congratulations! " + string(totalDeleted) + " posts have been deleted!"

# App run
app = Flask(__name__)
@app.route('/slack/app_mention', methods=[GET, POST])
def mention():
	if request.method == POST:
		if not request.is_json():
			return "not json error"
		postData = request.get_json()
		actionUser = postData["event"]["user"]
		if postData["event"]["type"] == "app_mention":
			content = postData["event"]["text"]
			if re.match(patternListAll, content):
				result = "wait..."
			elif re.match(patternListOne, content):
				user = re.match(patternAdd, content).group(1)
				result = ArtsList(queryType="user", query=user)
			elif re.match(patternLatest, content):
				count = re.match(patternAdd, content).group(1)
				result = ArtsList(queryType="latest", int(count))
			elif re.match(patternAdd, content):
				listToAdd = re.match(patternAdd, content).group(1).split(',')
				listToAdd.remove('')
				result = ArtsAdd(listToAdd)
			elif re.match(patternDel, content):
				listToDel = re.match(patternDel, content).group(1).split(',')
				listToDel.remove('')
				result = ArtsDel(listToDel)
			elif re.match(patternSetTarget, content):
				target = re.match(patternDel, content).group(1)
				result = StatusSet(actionUser, target)
			elif re.match(patternGetTarget, content):
				result = StatusGet(actionUser)
			elif re.match(patternRandom, content):
				count = re.match(patternAdd, content).group(1)
				result = ArtsList(queryType="rand", int(count))
			else:
				return "rule"
if __name__ == '__main__':
	app.run()