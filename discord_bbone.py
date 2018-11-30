import discord
from discord.compat import create_task
import mysql.connector
import asyncio
import spotify_api as sapi

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

# Variables
PREF = settingsDict['prefix']
boundChannels = '516168648373698563' #settingsDict['boundChannels']
DISCORDTOKEN = 'NTE2MTY5MTUxODQ1MzY3ODA5.DtvvnQ.3x4uiFEM5OlXrXeqPuMDBIfOtKY'
# DISCORDTOKEN = settingsDict['discordToken']
# <----->

client = discord.Client()

async def statusChange():
    await client.wait_until_ready()
    while not client.is_closed:
        while 1:
            await client.change_presence(game = discord.Game(name='SLAB v1'))
            await asyncio.sleep(15)
            helpStr = 'Type %shelp for help!' % PREF
            await client.change_presence(game = discord.Game(name=helpStr))
            await asyncio.sleep(15)

@client.event
async def on_message(message):
    global PREF
    global boundChannels
    
    if message.author == client.user:
        return
    if message.author.bot: return
    
    if message.channel.id in boundChannels:
        if message.content.lower().startswith('%shello' % PREF):
            msg = 'Hello {0.author.mention}'.format(message)
            await client.send_message(message.channel, msg)
            print('Received command > hello')
            
        elif message.content.lower().startswith('%ssearch' % PREF):
            msg = message.content.lower()
            msgList = msg.split()
            msgList.pop(0)
            
            if msgList == []:
                await client.send_message(message.channel, ':x:** Proper use:** `%ssearch <query>`' % PREF)
                return
            
            msg = ' '.join(msgList)
            print('Received command > search >> %s' % msg)
            # await client.send_message(message.channel, msg)
            response = sapi.searchSong(msg)
            
            if response == 'Something went wrong. Try again.':
                await client.send_message(message.channel, response)
                
            elif response == 'No results.':
                await client.send_message(message.channel, response)
                
            elif response != (('Something went wrong. Try again.') or ('No results.')):
                await client.send_message(message.channel, 'Is this the song you are looking for?')
                await client.send_message(message.channel, response[0])
                await client.send_message(message.channel, 'If yes, type \'**!!yes**\', and if not type \'**!!no**\' and specify your search')
                
                def agreement(ans):
                    if ans.content.startswith('%syes' % PREF):
                        return('yes')
                    else:
                        return('no')
                    
                ans = await client.wait_for_message(author=message.author, check=agreement, timeout=30)
                
                if ans.content == '{}yes'.format(PREF):
                    await client.send_message(message.channel, 'Adding to playlist')
                    response = sapi.addToPlaylist(response[1])
                    await client.send_message(message.channel, response)
                else:
                    await client.send_message(message.channel, 'Cancelled')
                    
        elif message.content.lower().startswith('%screate' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.user.id == '312223735505747968') == True:
                
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%screate <playlist name>`' % PREF)
                    return
                
                msg = ' '.join(msgList)
                print('Received command > create >> %s' % msg)
                response = sapi.createPlaylist(msg)
                
                if response[0] == 'Error creating playlist.':
                    await client.send_message(message.channel, response[0])
                    
                elif response[0] == 'Playlist already exists.':
                    await client.send_message(message.channel, response[0])
                    
                elif response[0] != 'Error creating playlist.' or 'Playlist already exists.':
                    await client.send_message(message.channel, response[0])
                    await client.send_message(message.channel, response[1]['playlist_url'])
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        elif message.content.lower().startswith('%sdelete' % PREF):
            print('Received command > delete')
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.user.id == '312223735505747968') == True:
                response = sapi.removePlaylist()
                
                if response == 'Deleted successfully.':
                    await client.send_message(message.channel, response)
                else:
                    await client.send_message(message.channel, response)
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        elif message.content.lower().startswith('%splaylist' % PREF):
            print('Received command > playlist')
            response = sapi.getPlaylist()
            await client.send_message(message.channel, response)
            
        elif message.content.lower().startswith('%sprefix' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.user.id == '312223735505747968') == True:
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%sprefix <prefix>`' % PREF)
                    return
                
                msg = ' '.join(msgList)
                print('Received command > prefix >> %s' % msg)
                PREF = msg
                await client.send_message(message.channel, 'Changed prefix to `%s`' % PREF)
                sapi.dbUpdateSettings((['prefix', PREF]))
                return PREF
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        elif message.content.lower().startswith('%shelp' % PREF):
            print('Received command > help')
            await client.send_message(message.channel, 'Available commands:\n```%sverify - allows you to verify your Spofity account\n%ssearch <query> - searches for a song to add it to playlist\n%splaylist - shows the playlist\n%shelp - shows this help```\nAdditional commands for admins:\n```%screate <name> - creates playlist with name <name>\n%sdelete - deletes playlist\n%sprefix <new prefix> - sets the prefix\n%sbind - binds bot to specified channel (where it accepts commands)```\n**NOTE:** Bot only allows for one playlist for now!' % (PREF, PREF, PREF, PREF, PREF, PREF, PREF, PREF))
            
        elif message.content.lower().startswith('%sverify' % PREF):
            print('Received command > verify')
            serverObj = client.get_server(message.server.id)
            memberObj = message.author
            response = sapi.verifyPremiumStep1()
            await client.send_message(message.author, ('To verify the account go to the following page and paste in the token:\n' + response))
            answ = await client.wait_for_message(author=message.author, timeout=60)
            authResponse = sapi.verifyPremiumStep2(answ.content)
            if authResponse == True:
                await client.send_message(message.author, 'You have premium subscription. You just got \'premium :star:\' role')
                role = discord.utils.get(serverObj.roles, name='PREMIUM ⭐')
                await client.add_roles(memberObj, role)
            elif authResponse == False:
                await client.send_message(message.author, 'You don\'t have a premium subscribtion')
            else:
                await client.send_message(message.author, authResponse)

        elif message.content.lower().startswith('%sdebug' % PREF):
            print('Received command > debug')
            clientVar = client
            serverVar = client.get_server(message.server.id)
            await asyncio.sleep(5)
    elif message.content.lower().startswith('%sbind' % PREF):
        print('Received command > bind')
        if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.user.id == '312223735505747968') == True:
            if message.channel.id in boundChannels:
                await client.send_message(message.channel, 'Already bound')
            else:
                boundChannels.append(message.channel.id)
                await client.send_message(message.channel, '***Bound to this channel.***')
                return boundChannels
        else:
            await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.loop.create_task(statusChange())
client.run(DISCORDTOKEN)
