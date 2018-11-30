## Imports
import mysql.connector
import requests as rq
import base64
import json
import webbrowser as wb

## MySQL
database = mysql.connector.connect(
	host='db4free.net',
	user='slabbot',
	passwd='Zabciajest10/10',
	database='slabbotdb'
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
    usersWhoAddedStr = playlistDict['usersWhoAdded']
    usersWhoAddedList = usersWhoAddedStr.split()
    playlistDict['usersWhoAdded'] = usersWhoAddedList
    playlistsList.append(playlistDict)

## Variables
accessToken = settingsDict['spotifyAccessToken']
refreshToken = settingsDict['spotifyRefreshToken']
clientID = settingsDict['spotifyCliendID']
clientSecret = settingsDict['spotifyClientSecret']
header = {'Authorization': 'Bearer '+ accessToken}

## Functions
def dbUpdateSettings(*parameters):
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

def dbUpdatePlaylists(action, name = None, url = None, id = None, usersWhoAdded = 'none'):
    if action == 'create':
        global playlistsList
        sql = 'INSERT INTO playlists (name, url, id, usersWhoAdded) VALUES (\'%s\', \'%s\', \'%s\', \'%s\')' % (name, url, id, usersWhoAdded)
        botCursor.execute(sql)
        database.commit()
        botCursor.execute('SELECT * FROM playlists')
        playlists = botCursor.fetchall()
        fields = [item[0] for item in botCursor.description]
        playlistsList = []
        for i in range(len(playlists)):
            playlistDict = {}
            for k in range(len(playlists[i])):
                extendDict = {fields[k]: playlists[i][k]}
                playlistDict.update(extendDict)
            usersWhoAddedStr = playlistDict['usersWhoAdded']
            usersWhoAddedList = usersWhoAddedStr.split()
            playlistDict['usersWhoAdded'] = usersWhoAddedList
            playlistsList.append(playlistDict)
        return playlistsList

def tokenSwap():
	global clientID
	global clientSecret

	wb.open('https://accounts.spotify.com/authorize?client_id=d3df69ad53ad4fe0afe621a68a2e852b&response_type=code&redirect_uri=https://march3wqa.github.io/Spotiscord/index.html&scope=playlist-modify-public', new=2)
	apiCode = input('Code >> ')

	authKey = clientID + ':' + clientSecret
	authKeyBytes = str.encode(authKey)
	authKeyBytes = base64.b64encode(authKeyBytes)
	authKey = bytes.decode(authKeyBytes)
	authHeader = {'Authorization': 'Basic '+ authKey}
	dataBody = {'grant_type': 'authorization_code', 'code': apiCode, 'redirect_uri': 'https://march3wqa.github.io/Spotiscord/index.html'}

	resp = rq.post(url = 'https://accounts.spotify.com/api/token', data = dataBody, headers = authHeader)
	respJson = resp.json()

	if resp.status_code == 200:
		global accessToken
		global refreshToken
		global header
		accessToken = respJson['access_token']
		refreshToken = respJson['refresh_token']
		header['Authorization'] = 'Bearer '+ accessToken
		tokens = {'access_token': accessToken, 'refresh_token': refreshToken}
		tokensJson = json.dumps(tokens)
		with open('tokens.json', 'w') as f:
			json.dump(tokensJson, f)
		return accessToken, refreshToken, header
	else:
		print(respJson['error'] + ' >> ' + respJson['error_description'])
		return('Something went terribly wrong')
	
def tokenRefresh():
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
		tokens = {'access_token': accessToken, 'refresh_token': refreshToken}
		tokensJson = json.dumps(tokens)
		with open('tokens.json', 'w') as f:
			json.dump(tokensJson, f)
		return accessToken, header
	else:
		print(respJson['error'] + ' >> ' + respJson['error_description'])
		tokenSwap()

def searchSong(q, market = 'PL'):
	query = q.replace(' ', '%20')
	params = {'q': query, 'type': 'track', 'limit': 1, 'offset': 0, 'market': market}
	resp = rq.get(url = 'https://api.spotify.com/v1/search', params = params, headers = header)
	respJson = resp.json()
	with open('response.json', 'w') as f:
		json.dump(respJson, f)
	if resp.status_code == 200:
		if respJson['tracks']['items'] == []:
			if market == 'US':
				return('No results.')
			else:
			    searchSong(q, 'US')
		else:
			trackURL = respJson['tracks']['items'][0]['external_urls']['spotify']
			trackURI = respJson['tracks']['items'][0]['uri']
			return(trackURL, trackURI)
	else:
		if resp.status_code == 401:
			print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
			tokenRefresh()
			return('Something went wrong. Try again.')
		else:
			print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
			return('Something went wrong. Try again.')

def createPlaylist(name):
    dataPost = '{\"name\": \"%s\"}' % name
    customHeader = header
    headerAdditional = {'Content-Type': 'application/json'}
    customHeader.update(headerAdditional)

    resp = rq.post(url = 'https://api.spotify.com/v1/users/11172683931/playlists', data = dataPost, headers = customHeader)
    respJson = resp.json()

    if resp.status_code == 200 or resp.status_code == 201:
        global playlistsList
        global playlistURL
        global playlistID
        playlistID = respJson['id']
        playlistURL = respJson['external_urls']['spotify']
        playlistsList = dbUpdatePlaylists('create', name, playlistURL, playlistID)
        return playlistID, playlistURL, playlistsList
    else:
        print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
        return ['Error creating playlist.']

def removePlaylist():
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
        print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
        return('Unable to delete playlist.')

def addToPlaylist(uri):
    global playlistID
    url = 'https://api.spotify.com/v1/playlists/%s/tracks' % playlistID
    params = {'uris': uri}
    resp = rq.post(url = url, params = params, headers = header)

    if resp.status_code == 201:
        return('Added successfully.')
    else:
        respJson = resp.json()
        print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
        return('Unable to add to playlist.')

def getPlaylist():
    global playlistURL
    return playlistURL

def verifyPremiumStep1():
    baseUrl = 'https://accounts.spotify.com/authorize'
    queryParams = 'client_id={}&response_type=token&redirect_uri=https://march3wqa.github.io/Spotiscord/index.html&scope=user-read-email%20user-read-private%20user-read-birthdate'
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
        print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
        return(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
