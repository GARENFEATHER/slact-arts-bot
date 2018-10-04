from flask import Flask, request, jsonify
import os, re, redis, requests

# Project Data
GET, POST = "GET", "POST"
projectKey, projectName, projectOauth = os.getenv("PROJECT_KEY"), os.getenv("PROJECT_NAME"), os.getenv("TOKEN_SLACK")
if not projectKey:
	raise Exception('no project key detected!')
if not projectName:
	raise Exception('no project name detected!')
if not projectOauth:
	raise Exception('no slack token detected!')
projectRule, projectToken, projectLatest, projectTotal = "default rule", projectKey+"-token-slack", projectKey + "-latest", projectKey + "-total"
patternListAll = "^<@.+> list all$"
patternListOne = "^<@.+> list <@(.+)> +$"
patternLatest = "^<@.+> latest ([1-9])$"
patternAdd = "^<@.+> add\n((<http[s]*://.+>\n)+)$"
patternDel = "^<@.+> delete\n((<http[s]*://.+>\n)+)$"
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

def GlobalProjectKeySet(projectId, ChannelId):
	global projectKey
	global projectToken
	global projectLatest
	global projectTotal
	global projectName
	global projectRule
	projectKey = projectId + "-" + ChannelId
	projectToken, projectLatest, projectTotal = projectKey+"-token-slack", projectKey + "-latest", projectKey + "-total"
	tmp = r.get("project-name-" + projectKey)
	if tmp:
		projectName = tmp
	else:
		headers = {"Content-type": "application/json", "Authorization":"Bearer " + projectOauth}
		resp = requests.get(url="https://slack.com/api/channels.info?channel="+ChannelId, headers=headers)
		respData = resp.json()
		print respData
		if respData["ok"] and respData["channel"]["is_channel"]:
			r.set("project-name-" + projectKey, respData["channel"]["name"])
			projectName = respData["channel"]["name"]
		else:
			projectName = "tmp"
	lineSep = "------------------------------------------------"
	projectRule = "1. list all " + projectName + "\n@me list all\n" + lineSep + "\n2. list someone's "
	projectRule += projectName + "\n@me list @someone\n" + lineSep + "\n3. get latest added " + projectName
	projectRule += "\n@me latest (count, 1-9)\n" + lineSep + "\n4. set " + projectName
	projectRule += " target\n@me set target (count)\n" + lineSep + "\n5. get my target\n@me get target\n" + lineSep + "\n6. random show " + projectName
	projectRule += "\n@me give me (count, 1-9)!\n" + lineSep + "\n7. add/delete my record for " + projectName + "\n@me add/delete\nrecord1\nrecord2\n..."

# Process Method
def ArtsList(queryType, query):
	if queryType == "rand":
		totalGet, respStr = set(), "rand " + projectName + " recommended for you:\n"
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
			return "sorry... no latest " + projectName + " list now"
		else:
			respStr = "latest added " + projectName +" here:\n"
			for i in range(len(latest)):
				respStr += str(i) + ": " + latest[i] + "\n"
			return respStr
	elif queryType == "user":
		userArts = r.smembers(projectKey + "-" + query)
		if len(userArts) != 0:
			respStr = projectName + " you've added:\n"
			for arts in userArts:
				respStr += arts + "\n"
			return respStr
		else:
			return "this guy has never added " + projectName + " !"

def TargetSet(user, value):
	result = r.set(projectKey + "-" + user + "-target", value)
	print "r.set, key:" + projectKey + "-" + user + "-target, value:", value, 
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
			print "r.sadd, key:", projectTotal+", value:", url
			totalAdded += 1
			r.sadd(projectKey + "-" + user, url)
			print "r.sadd, key:", projectKey + "-" + user + ", value:", url
			r.rpush(projectLatest, url)
			print "r.rpush, key:", projectLatest + ", value:", url
			count = r.llen(projectLatest)
			if count > 100:
				r.lpop(projectLatest)
				print "r.lpop, key:", projectLatest
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
			print "r.srem, key:", projectKey + "-" + user + ", value:", url
			r.lrem(projectLatest, 0, url)
			print "r.srem, key:", projectLatest + ", value:", url
	if totalDeleted == 0:
		return "nothing has benn deleted ..."
	elif totalDeleted == 1:
		return "congratulations! 1 post has been deleted!"
	else:
		return "congratulations! " + str(totalDeleted) + " posts have been deleted!"

def SendMessageToSlack(channelId, text):
	message = {"channel":channelId, "text":text, "token":projectOauth}
	headers = {"Content-type": "application/json", "Authorization":"Bearer " + projectOauth}
	resp = requests.post(url="https://slack.com/api/chat.postMessage", headers = headers, json = message)
	print "resp from slack:", resp.json()["ok"]

# App run
app = Flask(__name__)
@app.route('/', methods=[GET])
def hello():
	return "hello slack bot center by rhine"

@app.route('/api/v1.0/arts', methods=[GET, POST])
def mention():
	if request.method == POST:
		if not request.is_json:
			return "not json error"
		postData = request.get_json()
		if postData["type"] == "url_verification":
			return jsonify({"challenge":postData["challenge"]})
		actionUser = postData["event"]["user"]
		GlobalProjectKeySet(postData["team_id"], postData["event"]["channel"])
		if postData["event"]["type"] == "app_mention":
			content = postData["event"]["text"]
			print "content: ", content
			if re.match(patternListAll, content):
				text = "wait..."
			elif re.match(patternListOne, content):
				user = re.match(patternListOne, content).group(1)
				text = ArtsList(queryType="user", query=user)
			elif re.match(patternLatest, content):
				count = re.match(patternLatest, content).group(1)
				text = ArtsList(queryType="latest", query=int(count))
			elif re.match(patternAdd, content):
				listToAdd = re.match(patternAdd, content).group(1).split("\n")
				listToAdd.remove('')
				text = ArtsAdd(listToAdd, actionUser)
			elif re.match(patternDel, content):
				listToDel = re.match(patternDel, content).group(1).split("\n")
				listToDel.remove('')
				text = ArtsDel(listToDel, actionUser)
			elif re.match(patternSetTarget, content):
				target = re.match(patternSetTarget, content).group(1)
				text = TargetSet(actionUser, target)
			elif re.match(patternGetTarget, content):
				text = StatusGet(actionUser)
			elif re.match(patternRandom, content):
				count = re.match(patternRandom, content).group(1)
				text = ArtsList(queryType="rand", query=int(count))
			else:
				text = projectRule
		SendMessageToSlack(postData["event"]["channel"], text)
		return jsonify({"status":"ok"})
if __name__ == '__main__':
	port = int(os.getenv("PORT"))
	app.run(host='0.0.0.0', port=port)