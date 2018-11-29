## Imports
import requests as rq
import base64
import json
import webbrowser as wb

with open('tokens.json') as f:
	tokensStr = json.load(f)
	tokens = json.loads(tokensStr)

with open('playlists.json') as f:
	playlistsStr = json.load(f)
	playlists = json.loads(playlistsStr)

## Variables
playlistURL = playlists["playlist_url"]
playlistID = playlists["playlist_id"]
accessToken = tokens["access_token"]
refreshToken = tokens["refresh_token"]
clientID = 'd3df69ad53ad4fe0afe621a68a2e852b'
clientSecret = '9d998fca5b7444aa9ebf43c590e5d5c6'
header = {'Authorization': 'Bearer '+ accessToken}

## Functions
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
    global playlistID
    if playlistID == 'none':
        dataPost = '{\"name\": \"%s\"}' % name
        customHeader = header
        headerAdditional = {'Content-Type': 'application/json'}
        customHeader.update(headerAdditional)

        resp = rq.post(url = 'https://api.spotify.com/v1/users/11172683931/playlists', data = dataPost, headers = customHeader)
        respJson = resp.json()

        if resp.status_code == 200 or resp.status_code == 201:
            global playlistURL
            playlistID = respJson['id']
            playlistURL = respJson['external_urls']['spotify']
            playlists = {'playlist_url': playlistURL, 'playlist_id': playlistID}
            playlistsJson = json.dumps(playlists)
            with open('playlists.json', 'w') as f:
                json.dump(playlistsJson, f)
            return ['Created playlist: **%s**' % name, playlists]
        else:
            print(str(respJson['error']['status']) + ' >> ' + respJson['error']['message'])
            return ['Error creating playlist.']
    else:
        return ['Playlist already exists.']

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

