## Imports
import mysql.connector
import requests as rq
import os
import base64
import json
import webbrowser as wb
import logging
import asyncio


## MySQL
database = mysql.connector.connect(
	host=os.environ['db-host'],
	user=os.environ['db-user'],
	passwd=os.environ['db-passwd'],
	database=os.environ['db-dbname']
)
botCursor = database.cursor()

botCursor.execute('SELECT * FROM bot_settings')
settings = botCursor.fetchone()
fields = [item[0] for item in botCursor.description]
settingsDict = {}
for i in range(len(settings)):
	extendDict = {fields[i]: settings[i]}
	settingsDict.update(extendDict)
boundChannelsStr = settingsDict['boundChannels']
boundChannelsList = boundChannelsStr.split()
settingsDict['boundChannels'] = boundChannelsList

botCursor.execute('SELECT * FROM playlists')
playlists = botCursor.fetchall()
fields = [item[0] for item in botCursor.description]
playlistsList = []
for i in range(len(playlists)):
	playlistDict = {}
	for k in range(len(playlists[i])):
		extendDict = {fields[k]: playlists[i][k]}
		playlistDict.update(extendDict)
	if not playlistDict['users'] == None:
		users = playlistDict['users']
		usersList = users.split()
		playlistDict['users'] = usersList
	playlistsList.append(playlistDict)

## Variables
logger = logging.getLogger('SpotifyAPI')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s || %(levelname)s: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
accessToken = settingsDict['spotifyAccessToken']
refreshToken = settingsDict['spotifyRefreshToken']
clientID = settingsDict['spotifyCliendID']
clientSecret = settingsDict['spotifyClientSecret']
header = {'Authorization': 'Bearer '+ accessToken}

## Functions
async def dbUpdateSettings(*parameters):
	parametersStr = ''
	for i in range(len(parameters)):
		parametersStr = parametersStr + parameters[i][0] + ' = \'' + parameters[i][1] + '\''
		if i == len(parameters)-1:
			pass
		else:
			parametersStr = parametersStr + ', '
	sql = 'UPDATE bot_settings SET %s' % parametersStr
	botCursor.execute(sql)
	database.commit()

### * Add delete song functionality
async def dbUpdatePlaylists(action, name = None, url = None, ID = None, user = None):
	global playlistsList
	if action == 'create':
		sql = 'INSERT INTO playlists (name, url, id) VALUES (\'%s\', \'%s\', \'%s\')' % (name, url, ID)
		botCursor.execute(sql)
		database.commit()
	elif action == 'update':
		if user == None:
			sql = 'UPDATE playlists SET users = \'%s\' WHERE name = \'%s\'' % (user, name)
		else:
			for i in len(playlistsList):
				if playlistsList[i]['name'] == name:
					currUsers = playlistsList[i]['users']
					currUsers.append(user)
					currUsersStr = ' '.join(currUsers)
					sql = 'UPDATE playlists SET users = \'%s\' WHERE name = \'%s\'' % (currUsersStr, name)
		botCursor.execute(sql)
		botCursor.commit()
	else:
		return(1)
	botCursor.execute('SELECT * FROM playlists')
	playlists = botCursor.fetchall()
	fields = [item[0] for item in botCursor.description]
	playlistsList = []
	for i in range(len(playlists)):
		playlistDict = {}
		for k in range(len(playlists[i])):
			extendDict = {fields[k]: playlists[i][k]}
			playlistDict.update(extendDict)
		users = playlistDict['users']
		usersList = users.split()
		playlistDict['users'] = usersList
		playlistsList.append(playlistDict)
	return playlistsList

async def tokenSwap():
	global clientID
	global clientSecret

	# wb.open('https://accounts.spotify.com/authorize?client_id=d3df69ad53ad4fe0afe621a68a2e852b&response_type=code&redirect_uri=https://march3wqa.github.io/SLAB/oauth/tokenswap/index.html&scope=playlist-modify-public', new=2)
	print('https://accounts.spotify.com/authorize?client_id=d3df69ad53ad4fe0afe621a68a2e852b&response_type=code&redirect_uri=https://march3wqa.github.io/SLAB/oauth/tokenswap/index.html&scope=playlist-modify-public')
	apiCode = input('Code >> ')

	authKey = clientID + ':' + clientSecret
	authKeyBytes = str.encode(authKey)
	authKeyBytes = base64.b64encode(authKeyBytes)
	authKey = bytes.decode(authKeyBytes)
	authHeader = {'Authorization': 'Basic '+ authKey}
	dataBody = {'grant_type': 'authorization_code', 'code': apiCode, 'redirect_uri': 'https://march3wqa.github.io/SLAB/oauth/tokenswap/index.html'}

	resp = rq.post(url = 'https://accounts.spotify.com/api/token', data = dataBody, headers = authHeader)
	respJson = resp.json()

	if resp.status_code == 200:
		global accessToken
		global refreshToken
		global header
		accessToken = respJson['access_token']
		refreshToken = respJson['refresh_token']
		header['Authorization'] = 'Bearer '+ accessToken
		dbUpdateSettings(['spotifyAccessToken', accessToken], ['spotifyRefreshToken', refreshToken])
		return accessToken, refreshToken, header
	else:
		logger.critical((respJson['error'] + ' >> ' + respJson['error_description']))
		return('Something went terribly wrong')
	
async def tokenRefresh(): 
	global accessToken
	global refreshToken

	dataBody = {'grant_type': 'refresh_token', 'refresh_token': refreshToken}
	authKey = clientID + ':' + clientSecret
	authKeyBytes = str.encode(authKey)
	authKeyBytes = base64.b64encode(authKeyBytes)
	authKey = bytes.decode(authKeyBytes)
	authHeader = {'Authorization': 'Basic '+ authKey}

	resp = rq.post(url = 'https://accounts.spotify.com/api/token', data = dataBody, headers = authHeader)
	respJson = resp.json()

	if resp.status_code == 200:
		global header
		accessToken = respJson['access_token']
		header['Authorization'] = 'Bearer '+ accessToken
		dbUpdateSettings(['spotifyAccessToken', accessToken])
		return accessToken, header
	else:
		logger.error((respJson['error'] + ' >> ' + respJson['error_description']))
		await tokenSwap()

### /TODO/: Add search by URI
async def searchSong(q):
	if q[:14] == 'spotify:track:':
		query = q.split(':')
		query = query[2]
		url = 'https://api.spotify.com/v1/tracks/{}'.format(query)
		qType = 'id'
	else:
		query = q.replace(' ', '%20')
		params = {'q': query, 'type': 'track', 'limit': 1}
		url = 'https://api.spotify.com/v1/search?'
		url = url+'q='+params['q']+'&type='+params['type']+'&limit='+str(params['limit'])
		qType = 'normal'
	resp = rq.get(url = url, headers = header)
	respJson = resp.json()
	if resp.status_code == 200:
		if qType == 'normal':
			if respJson['tracks']['items'] == []:
				return([2])
			else:
				trackURL = respJson['tracks']['items'][0]['external_urls']['spotify']
				trackID = respJson['tracks']['items'][0]['id']
				return(0, trackURL, trackID)
		elif qType == 'id':
			trackURL = respJson['external_urls']['spotify']
			trackID = respJson['id']
			return(0, trackURL, trackID)
	else:
		if resp.status_code == 401:
			logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
			logger.warning(('~~ Trying to get new token and retry search'))
			await tokenRefresh()
			return await searchSong(q)
		elif resp.status_code == 400:
			logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
			if respJson['error']['message'] == 'invalid id':
				return([3])
			logger.warning(('~~ Trying to get new token pair and retry search'))
			await tokenSwap()
			return await searchSong(q)
		elif resp.status_code == 404:
			return([4])
		else:
			logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
			return([1])

def createPlaylist(name):
	dataPost = '{\"name\": \"%s\"}' % name
	customHeader = header
	headerAdditional = {'Content-Type': 'application/json'}
	customHeader.update(headerAdditional)

	resp = rq.post(url = 'https://api.spotify.com/v1/users/11172683931/playlists', data = dataPost, headers = customHeader)
	respJson = resp.json()

	if resp.status_code == 200 or resp.status_code == 201:
		global playlistsList
		playlistID = respJson['id']
		playlistURL = respJson['external_urls']['spotify']
		playlistsList = dbUpdatePlaylists('create', name, playlistURL, playlistID)
		return playlistsList
	else:
		logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
		return ['Error creating playlist.']

def removePlaylist(name):
	global playlistID
	global playlistURL
	url = 'https://api.spotify.com/v1/playlists/%s/followers' % playlistID
	resp = rq.delete(url = url, headers = header)

	if resp.status_code == 200:
		playlists = {'playlist_url': 'none', 'playlist_id': 'none'}
		playlistsJson = json.dumps(playlists)
		with open('playlists.json', 'w') as f:
			json.dump(playlistsJson, f)
		return('Deleted successfully.')
	else:
		respJson = resp.json()
		logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
		return('Unable to delete playlist.')

def addToPlaylist(playlistName, id, user):
	global playlistsList
	if any(d['name'] == playlistName for d in playlistsList):
		for i in len(playlistsList):
					if playlistsList[i]['name'] == playlistName:
						playlistID = playlistsList[i]['id']
		url = 'https://api.spotify.com/v1/playlists/%s/tracks' % playlistID
		params = {'uris': 'spotify:track:{}'.format(id)}
		resp = rq.post(url = url, params = params, headers = header)

		if resp.status_code == 201:
			playlistsList = dbUpdatePlaylists('update', name=playlistName, user=user)

			return(0, playlistsList)
		else:
			respJson = resp.json()
			logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
			return(1)
	else:
		return(2)

### TODO: Get playlist by name
def getPlaylist(name):
	pass

def verifyPremiumStep1():
	baseUrl = 'https://accounts.spotify.com/authorize'
	queryParams = 'client_id={}&response_type=token&redirect_uri=https://march3wqa.github.io/SLAB/oauth/token/index.html&scope=user-read-private'
	finalUrl = baseUrl + '?' + queryParams.format(clientID)
	return finalUrl

def verifyPremiumStep2(token):
	authHeader = {'Authorization': 'Bearer ' + token}
	resp = rq.get(url='https://api.spotify.com/v1/me', headers=authHeader)
	respJson = resp.json()
	if resp.status_code == 200:
		if respJson['product'] == 'premium':
			return True
		else:
			return False
	else:
		logger.error((str(respJson['error']['status']) + ' >> ' + respJson['error']['message']))
		return(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
