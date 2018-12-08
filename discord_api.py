import discord
from discord.compat import create_task
import mysql.connector
import asyncio
from spotify_api import *
import os
import logging
import threading
import signal

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

# Variables & classes
stopCode = False
logger = logging.getLogger('DiscordAPI')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s || %(levelname)s: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
PREF = settingsDict['prefix']
boundChannels = settingsDict['boundChannels']
DISCORDTOKEN = settingsDict['discordToken']
clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
# <----->

client = discord.Client()

def sigterm_handler(signal, frame):
    stopCode = True
    raise SystemExit
signal.signal(signal.SIGTERM, sigterm_handler)

async def statusChange():
    global statusRun
    if os.environ['bot-build'] == 'dev':
        suffix = '-dev'
    elif os.environ['bot-build'] == 'stable':
        suffix = '-stable'
    await client.wait_until_ready()
    while 1:
        try:
            await client.change_presence(game = discord.Game(name='SLAB v1{}'.format(suffix)))
            await asyncio.sleep(15)
            helpStr = 'Type %shelp for help!' % PREF
            await client.change_presence(game = discord.Game(name=helpStr))
            await asyncio.sleep(15)
        except BaseException as err:
            logger.critical('Exception occurred: {} '.format(err))
            client.connect()
            break

@client.event
async def on_message(message):
    await client.wait_until_ready()
    global PREF
    global boundChannels
    
    if message.author == client.user:
        return
    if message.author.bot: return

    if message.content.lower().startswith('%sbind' % PREF):
        logger.info(('Received command > bind | From {0.author} in {0.server.name}/{0.channel}'.format(message)))
        if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:
            if message.channel.id in boundChannels:
                await client.send_message(message.channel, 'Already bound')
            else:
                boundChannels.append(message.channel.id)
                sapi.dbUpdateSettings(['boundChannels', ' '.join(boundChannels)])
                await client.send_message(message.channel, '***Bound to this channel.***')
                return boundChannels
        else:
            await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
    
    if message.content.lower().startswith('%sunbind' % PREF):
        print('Received command > unbind | From {0.author} in {0.server.name}/{0.channel}'.format(message))
        if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:
            if message.channel.id not in boundChannels:
                await client.send_message(message.channel, 'Not binded')
            else:
                boundChannels.remove(message.channel.id)
                sapi.dbUpdateSettings(['boundChannels', ' '.join(boundChannels)])
                await client.send_message(message.channel, '***Unbound from this channel.***')
                return boundChannels
        else:
            await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')

    elif message.channel.id in boundChannels:
        ### ? Should this even be here?
        if message.content.lower().startswith('%shello' % PREF):
            msg = 'Hello {0.author.mention}'.format(message)
            await client.send_message(message.channel, msg)
            logger.info(('Received command > hello | From {0.author} in {0.server.name}/{0.channel}'.format(message)))
            
        elif message.content.lower().startswith('%ssearch' % PREF):
            msg = message.content
            msgList = msg.split()
            msgList.pop(0)
            
            if msgList == []:
                await client.send_message(message.channel, ':x:** Proper use:** `%ssearch <query/song URI>`' % PREF)
                return
            
            msg = ' '.join(msgList)
            logger.info(('Received command > search >> {1} | From {0.author} in {0.server.name}/{0.channel}'.format(message, msg)))
            # await client.send_message(message.channel, msg)
            response = await searchSong(msg)
            
            if response[0] == 1:
                await client.send_message(message.channel, 'Something went wrong. Try again.')
                
            elif response[0] == 2:
                await client.send_message(message.channel, 'No results.')

            elif response[0] == 3:
                await client.send_message(message.channel, 'Invalid URI. Try copying/pasting it again.')
            
            elif response[0] == 4:
                await client.send_message(message.channel, 'No track with that URI. Try copying/pasting it again.')
                
            elif response[0] == 0:
                await client.send_message(message.channel, 'Is this the song you are looking for?')
                await client.send_message(message.channel, response[1])
                await client.send_message(message.channel, 'If yes, type `{0}yes <playlist\'s name>` to add to playlist or `{0}no` to cancel'.format(PREF))
                
                def agreement(ans):
                    if ans.content.lower().startswith('%syes' % PREF):
                        return('yes')
                    else:
                        return('no')
                    
                ans = await client.wait_for_message(author=message.author, check=agreement, timeout=30)
                
                if ans.content.lower().startswith('{}yes'.format(PREF)):
                    plName = ans.content
                    plName = plName.split()
                    plName.pop(0)
                    plName = ''.join(plName)
                    await client.send_message(message.channel, 'Adding to playlist...')
                    addResp = await addToPlaylist(plName, response[2], message.author.id)
                    if addResp[0] == 0:
                        await client.send_message(message.channel, 'Successfully added to playlist `{}`'.format(plName))
                    elif addResp[0] == 1:
                        await client.send_message(message.channel, 'Unable to add to playlist `{}`'.format(plName))
                    elif addResp[0] == 2:
                        await client.send_message(message.channel, 'No playlist named `{}`'.format(plName))
                    elif addResp[0] == 3:
                        await client.send_message(message.channel, 'Authorization failure. Contact your admin.')
                elif ans.clean_content.lower().startswith('{}no'.format(PREF)):
                    await client.send_message(message.channel, 'Cancelled.')
                else:
                    await client.send_message(message.channel, 'Invalid answer. Cancelling.')
                    
        elif message.content.lower().startswith('%screateplaylist' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:
                
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%screateplaylist <playlist name>`' % PREF)
                    return
                
                msg = ' '.join(msgList)
                logger.info(('Received command > create >> {1} | From {0.author} in {0.server.name}/{0.channel}'.format(message, msg)))
                response = await createPlaylist(msg)
                
                if response[0] == 1:
                    await client.send_message(message.channel, 'Error creating playlist.')
                    
                elif response[0] == 2:
                    await client.send_message(message.channel, 'Playlist with that name already exists.')
                
                elif response[0] == 3:
                    await client.send_message(message.channel, 'Invalid character(s). Remove or replace any non-ascii characters.')
                    
                elif response[0] == 0:
                    await client.send_message(message.channel, 'Successfully created playlist `{}`'.format(msg))
                    await client.send_message(message.channel, response[1])
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        elif message.content.lower().startswith('%sdeleteplaylist' % PREF):
            msg = message.content.lower()
            msgList = msg.split()
            msgList.pop(0)
            
            if msgList == []:
                await client.send_message(message.channel, ':x:** Proper use:** `%sdeleteplaylist <playlist name>`' % PREF)
                return
            
            msg = ' '.join(msgList)
            logger.info(('Received command > delete >> {1} | From {0.author} in {0.server.name}/{0.channel}'.format(message, msg)))
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:

                response = await removePlaylist(msg)
                
                if response[0] == 1:
                    await client.send_message(message.channel, 'Error deleting playlist.')
                    
                elif response[0] == 2:
                    await client.send_message(message.channel, 'No playlist with that name.')
                
                elif response[0] == 3:
                    await client.send_message(message.channel, 'Invalid character(s). Remove or replace any non-ascii characters.')
                    
                elif response[0] == 0:
                    await client.send_message(message.channel, 'Successfully deleted playlist `{}`'.format(msg))
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
        
        elif message.content.lower().startswith('%splaylists' % PREF):
            logger.info(('Received command > playlists | From {0.author} in {0.server.name}/{0.channel}'.format(message)))
            response = await getPlaylists()
            if response[0] == 1:
                await client.send_message(message.channel, 'Error getting playlists.')
            if response[0] == 2:
                await client.send_message(message.channel, 'No playlists.')
            elif response[0] == 0:
                user = await client.get_user_info('312223735505747968')
                playlistsEmbed = discord.Embed(color=discord.Color.green())
                playlistsEmbed.set_author(name='SLAB playlists', icon_url=client.connection.user.avatar_url)
                for item in response[1]:
                    playlistsEmbed.add_field(name=item[0], value=item[1], inline=True)
                playlistsEmbed.set_footer(text='Made with 💖 by {0.name}#{0.discriminator}'.format(user), icon_url=user.avatar_url)
                await client.send_message(message.channel, embed=playlistsEmbed)
            
        elif message.content.lower().startswith('%sprefix' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%sprefix <prefix>`' % PREF)
                    return
                
                msg = ' '.join(msgList)
                logger.info(('Received command > prefix >> {1} | From {0.author} in {0.server.name}/{0.channel}'.format(message, msg)))
                PREF = msg
                await client.send_message(message.channel, 'Changed prefix to `%s`' % PREF)
                sapi.dbUpdateSettings((['prefix', PREF]))
                return PREF
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        elif message.content.lower().startswith('%shelp' % PREF):
            logger.info(('Received command > help | From {0.author} in {0.server.name}/{0.channel}'.format(message)))
            user = await client.get_user_info('312223735505747968')
            helpEmbed = discord.Embed(
                color = discord.Color.green()
            )
            helpEmbed.set_author(name='SLAB Help', icon_url=client.connection.user.avatar_url)
            helpEmbed.add_field(name='%shelp'%PREF, value='Shows this help', inline=True)
            helpEmbed.add_field(name='%sverify'%PREF, value='Allows you to obtain Premium:star: role', inline=False)
            helpEmbed.add_field(name='%ssearch <query>'%PREF, value='Allows you to search for a song to add to playlist', inline=True)
            helpEmbed.add_field(name='%sdelete <uri> <playlist>'%PREF, value='Deletes song with <uri> from <playlist>', inline=True)
            helpEmbed.add_field(name='%splaylists'%PREF, value='Shows list of available playlists', inline=True)
            helpEmbed.add_field(name='%splaylist <name>'%PREF, value='Shows the requested playlist', inline=True)
            helpEmbed.add_field(name='%screateplaylist <name>'%PREF, value='Creates playlist with name <name>', inline=True)
            helpEmbed.add_field(name='%sdeleteplaylist <name>'%PREF, value='Deletes playlist with name <name>', inline=True)
            helpEmbed.add_field(name='%sprefix <prefix>'%PREF, value='Sets new <prefix> for commands', inline=True)
            helpEmbed.add_field(name='%sbind'%PREF, value='Binds bot to current channel', inline=True)
            helpEmbed.add_field(name='%sunbind'%PREF, value='Unbinds bot from current channel', inline=True)
            helpEmbed.set_footer(text='Made with 💖 by {0.name}#{0.discriminator}'.format(user), icon_url=user.avatar_url)
            await client.send_message(message.channel, embed=helpEmbed)

        elif message.content.lower().startswith('%sverify' % PREF):
            logger.info(('Received command > verify | From {0.author} in {0.server.name}/{0.channel}'.format(message)))
            serverObj = client.get_server(message.server.id)
            memberObj = message.author
            response = await verifyPremiumStep1()
            await client.send_message(message.author, ('To verify the account go to the following page and paste in the token:\n' + response))
            answ = await client.wait_for_message(author=message.author, timeout=600)
            authResponse = await verifyPremiumStep2(answ.content)
            if authResponse == True:
                await client.send_message(message.author, 'You have premium subscription. You just got `PREMIUM ⭐` role')
                role = discord.utils.get(serverObj.roles, name='PREMIUM ⭐')
                await client.add_roles(memberObj, role)
            elif authResponse == False:
                await client.send_message(message.author, 'You don\'t have a premium subscribtion')
            else:
                await client.send_message(message.author, authResponse)

        elif message.content.lower().startswith('%sdelete' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:
                msg = message.content
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%sdelete <song URI> <playlist name>`' % PREF)
                    return
                
                playlistName = ' '.join(msg[1:])
                logger.info(('Received command > delete >> {1} - {2}| From {0.author} in {0.server.name}/{0.channel}'.format(message, msg[0], playlistName)))
                response = await removeSong(msg[0], playlistName)

                if response[0] == 1:
                    await client.send_message(message.channel, 'Error deleting song.')
                elif response[0] == 2:
                    await client.send_message(message.channel, 'No playlists')
                elif response[0] == 3:
                    await client.send_message(message.channel, 'Invalid character(s). Remove or replace any non-ascii characters.')
                elif response[0] == 4:
                    await client.send_message(message.channel, 'No playlists with name `{}`'.format(msg[0]))
                elif response[0] == 0:
                    await client.send_message(message.channel, 'Song successfully removed.')
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')

        elif message.content.lower().startswith('%splaylist' % PREF):
            msg = message.content.lower()
            msgList = msg.split()
            msgList.pop(0)
            
            if msgList == []:
                await client.send_message(message.channel, ':x:** Proper use:** `%splaylist <playlist\'s name>`' % PREF)
                return
            
            msg = ' '.join(msgList)
            logger.info(('Received command > playlist >> {1} | From {0.author} in {0.server.name}/{0.channel}'.format(message, msg)))

            response = await getPlaylist(msg)

            if response[0] == 1:
                await client.send_message(message.channel, 'Something went wrong.')
            elif response[0] == 2:
                await client.send_message(message.channel, 'No playlists.')
            elif response[0] == 3:
                await client.send_message(message.channel, 'Invalid character(s). Remove or replace any non-ascii characters.')
            elif response[0] == 0:
                await client.send_message(message.channel, response[1])

        elif message.content.lower().startswith('%sclear' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) or (message.author.id == '312223735505747968') == True:
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                if msgList == []:
                    return
                limit = int(msgList[0])
                limit + 1
                limit = clamp(n=limit, minn=2, maxn=100)
                channel = message.channel
                messages = []
                async for message in client.logs_from(channel, limit=limit):
                    messages.append(message)
                await client.delete_messages(messages)

@client.event
async def on_ready():
    logger.info(('Logging in as:'))
    logger.info((client.user.name))
    logger.info((client.user.id))
    logger.info(('------'))

@client.event
async def on_resumed():
    logger.info('Reconnected')

if __name__ == "__main__":
    logger.info(('Starting code...'))
    client.loop.create_task(statusChange())
    while True:
        try:
            client.loop.run_until_complete(client.start(DISCORDTOKEN))
        except SystemExit as err:
            logger.info('Stopping code...')
            stopCode = True
            client.logout()
            logger.info('Stopped code')
        except KeyboardInterrupt as err:
            logger.info('Stopping code...')
            stopCode = True
            client.logout()
            logger.info('Stopped code')
        except BaseException as err:
            logger.critical('Exception occurred: {} '.format(err))
            logger.info('Trying to reconnect...')
        if stopCode: break
        