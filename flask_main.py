from flask import Flask, url_for, render_template, request, make_response, Markup
from flask_sslify import SSLify
import requests as rq
import discord, colorama, asyncio, mysql.connector, os, base64, threading, markdown
colorama.init(autoreset=True)

app = Flask(__name__)
ssl = SSLify(app)

# MySQL
cldb = os.environ['CLEARDB_DATABASE_URL']
cldb = cldb.split('@')
cldb[0] = cldb[0].replace('mysql://', '')
cred = cldb[0].split(':')
cldb[1] = cldb[1].replace('?reconnect=true', '')
uri = cldb[1].split('/')

database = mysql.connector.connect(
    host=uri[0],
    user=cred[0],
    passwd=cred[1],
    database=uri[1]
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
settingsDict['boundChannels'] = [int(chid) for chid in boundChannelsList]

accessToken = settingsDict['spotifyAccessToken']
refreshToken = settingsDict['spotifyRefreshToken']
clientID = settingsDict['spotifyCliendID']
clientSecret = settingsDict['spotifyClientSecret']
header = {'Authorization': 'Bearer ' + accessToken}
dscHeader = {'Authorization': 'Bot {}'.format(settingsDict['discordToken']), 'Content-Type': 'application/json', 'User-Agent': 'DiscordBot (+https://slab-discord.herokuapp.com/, 3.2)'}


@app.route('/callback', methods=['GET'])
def callback():
    try:
        global code
        global user
        code = request.args['code']
        user = request.args['state']
        t = threading.Thread(target=addRole, args=(code, user))
        t.start()
        return make_response(render_template('tokenswap/index.html'), 202)
    except KeyError as err:
        return make_response(render_template('tokenswap/error.html', exc=err), 400)
    except Exception as err:
        return make_response(render_template('tokenswap/error.html', exc=err), 500)

@app.route('/other/code_of_conduct')
def code_of_conduct():
    with open('templates/other/CODE_OF_CONDUCT.md', 'r') as f:
        content = f.read()
    content = Markup(markdown.markdown(content))
    return render_template('other/index.html', **locals())

@app.route('/other/templates/bug_report')
def bug_report():
    with open('templates/other/ISSUE_TEMPLATE/bug_report.md', 'r') as f:
        content = f.read()
    content = Markup(markdown.markdown(content))
    return render_template('other/index.html', **locals())

@app.route('/other/templates/feature_request')
def feature_request():
    with open('templates/other/ISSUE_TEMPLATE/feature_request.md', 'r') as f:
        content = f.read()
    content = Markup(markdown.markdown(content))
    return render_template('other/index.html', **locals())

def addRole(code, user):
    global clientID
    global clientSecret

    author = bytes.decode(base64.b64decode(str.encode(user)))
    authKey = clientID + ':' + clientSecret
    authKeyBytes = str.encode(authKey)
    authKeyBytes = base64.b64encode(authKeyBytes)
    authKey = bytes.decode(authKeyBytes)
    authHeader = {'Authorization': 'Basic ' + authKey}
    dataBody = {'grant_type': 'authorization_code', 'code': code,
                'redirect_uri': 'https://slab-discord.herokuapp.com/callback'}

    resp = rq.post(url='https://accounts.spotify.com/api/token', data=dataBody, headers=authHeader)
    respJson = resp.json()

    if resp.status_code == 200:
        aToken = respJson['access_token']
        rToken = respJson['refresh_token']

        sql = 'UPDATE users SET spotify_access_token = \'{}\', spotify_refresh_token = \'{}\', has_tokens = 1 WHERE discordid = \'{}\''.format(aToken, rToken, author)
        try:
            botCursor.execute(sql)
            database.commit()
        except BaseException as err:
            database.reconnect(100)
            botCursor.execute(sql)
            database.commit()
        
        authHeader = {'Authorization': 'Bearer ' + aToken}
        resp = rq.get(url='https://api.spotify.com/v1/me', headers=authHeader)
        respJson = resp.json()
        if resp.status_code == 200:
            if respJson['product'] == 'premium':
                sql = 'UPDATE users SET premium = 1 WHERE discordid = \'{}\''.format(author)
                try:
                    botCursor.execute(sql)
                    database.commit()
                except BaseException as err:
                    database.reconnect(100)
                    botCursor.execute(sql)
                    database.commit()

                #// REPLACE //#
                #// guildObj = client.get_guild(454888283927871508)
                #// role = guildObj.get_role(517775191632511006)
                #// member = guildObj.get_member(int(author))
                #// await member.send('executed')
                #// await member.add_roles(role, reason='Verified Spotify premium account')
                #// await client.close()
                #//#########//#
                #* NEW CODE *#
                guildID = '408958645745745942'
                roleID = '408976689625038848'
                global dscHeader
                newHeader = {}
                newHeader.update(dscHeader)
                newHeader.update({'X-Audit-Log-Reason': 'Verified Spotify premium account'})
                respPut = rq.put(url='https://discordapp.com/api/v6/guilds/{0}/members/{1}/roles/{2}'.format(guildID, author, roleID), headers=newHeader)
                if respPut.status_code == 204:
                    dmBody = {'recipient_id': author}
                    dmChannel = rq.post(url='https://discordapp.com/api/v6/users/@me/channels', headers=dscHeader, json=dmBody)
                    if dmChannel.status_code == 200:
                        dmJson = dmChannel.json()

                        message = {'content': 'You have premium subscription. You just got `PREMIUM ⭐` role!', 'tts': False, 'embed': None}
                        rq.post(url='https://discordapp.com/api/v6/channels/{0}/messages'.format(dmJson['id']), headers=dscHeader, json=message)
                #*##########*#
                return True
            dmBody = {'recipient_id': author}
            dmChannel = rq.post(url='https://discordapp.com/api/v6/users/@me/channels', headers=dscHeader, json=dmBody)
            if dmChannel.status_code == 200:
                dmJson = dmChannel.json()

                message = {'content': 'Unfortunately, your Spotify subscription isn\'t premium. If you think you have it, contact an administrator on the server or directly.', 'tts': False, 'embed': None}
                rq.post(url='https://discordapp.com/api/v6/channels/{0}/messages'.format(dmJson['id']), header=dscHeader, json=message)
    return False

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)