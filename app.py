from flask import Flask, request, jsonify
import os, re, redis

# Project Data
GET, POST = "GET", "POST"
projectKey = os.getenv("PROJECT_KEY")
if not projectKey:
	raise Exception('no project key detected!')
projectLatest = projectKey + "-latest"
projectTotal = projectKey + "-total"
patternListAll = "^<@.+> list all$"
patternListOne = "^<@.+> list <@(.+)>$"
patternLatest = "^<@.+> latest ([1-9])$"
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

# Test Connection
test, testRes = "test-global", "success"
r.set(test, testRes)
mark = r.get(test)
if mark != testRes:
	raise Exception("set test-global failed," + testRes + "/" + str(type(mark)) + str(type(testRes)))

# Process Method
def ArtsList(queryType, query):
	if queryType == "rand":
		totalGet, respStr = set(), "rand arts recommended for you:\n"
		total = r.scard(projectTotal)
		if total < query * 2:
			query = total
			respStr = "total added:" + str(total) + "\n" + respStr
		while len(totalGet) < query:
			url = r.srandmember(projectTotal)
			totalGet.add(url)# TODO: dead lock possible
		for i in range(len(totalGet)):
			respStr += str(i) + ": " + url + "\n"
		return respStr
	elif queryType == "latest":
		latest = r.lrange(projectLatest, query * -1, -1)
		if len(latest) == 0:
			return "sorry... no latest arts list now"
		else:
			respStr = "latest added arts here:\n"
			for i in range(len(latest)):
				respStr += str(i) + ": " + latest[i] + "\n"
			return respStr
	elif queryType == "user":
		userArts = r.smembers(projectKey + "-" + query)
		if len(userArts) != 0:
			respStr = "arts you've added:\n"
			for arts in userArts:
				respStr += arts + "\n"
			return respStr
		else:
			return "you've never added your arts, add one now!"

def TargetSet(user, value):
	result = r.set(projectKey + "-" + user + "-target", value)
	if result:
		return "target successfully set, new target:" + str(value)
	else:
		return "target set failed...sorry, please check again"

def StatusGet(user):
	targetBefore = r.get(projectKey + "-" + user + "-target")
	addedCount = r.scard(projectKey + "-" + user)
	if not targetBefore:
		return "no target now...let's set one!" + "\nyou've added:" + str(addedCount)
	else:
		return "your target:" + str(targetBefore) + "\nyou've added:" + str(addedCount)

def ArtsAdd(listToAdd, user):
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
		return "congratulations! " + str(totalAdded) + " posts have been added!"

def ArtsDel(listToDelete, user):
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
		return "congratulations! " + str(totalDeleted) + " posts have been deleted!"

# App run
app = Flask(__name__)
@app.route('/', methods=[GET, POST])
def hello():
	return "hello slack arts bot"

@app.route('/slack/app_mention', methods=[GET, POST])
def mention():
	if request.method == POST:
		if not request.is_json:
			return "not json error"
		postData = request.get_json()
		actionUser = postData["event"]["user"]
		if postData["event"]["type"] == "app_mention":
			content = postData["event"]["text"]
			if re.match(patternListAll, content):
				result = "wait..."
			elif re.match(patternListOne, content):
				user = re.match(patternListOne, content).group(1)
				result = ArtsList(queryType="user", query=user)
			elif re.match(patternLatest, content):
				count = re.match(patternLatest, content).group(1)
				result = ArtsList(queryType="latest", query=int(count))
			elif re.match(patternAdd, content):
				listToAdd = re.match(patternAdd, content).group(1).split(',')
				listToAdd.remove('')
				result = ArtsAdd(listToAdd, actionUser)
			elif re.match(patternDel, content):
				listToDel = re.match(patternDel, content).group(1).split(',')
				listToDel.remove('')
				result = ArtsDel(listToDel, actionUser)
			elif re.match(patternSetTarget, content):
				target = re.match(patternSetTarget, content).group(1)
				result = TargetSet(actionUser, target)
			elif re.match(patternGetTarget, content):
				result = StatusGet(actionUser)
			elif re.match(patternRandom, content):
				count = re.match(patternRandom, content).group(1)
				result = ArtsList(queryType="rand", query=int(count))
			else:
				result = "rule"
		return jsonify({"result":result})
if __name__ == '__main__':
	port = int(os.getenv("PORT"))
	app.run(host='0.0.0.0', port=port)