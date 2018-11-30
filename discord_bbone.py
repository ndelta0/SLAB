import discord
from discord.compat import create_task

import asyncio
import spotify_api as sapi


# Variables
PREF = '!!'
boundChannels = ['409066385453613079']
# DISCORDTOKEN = 'NTE2MTY5MTUxODQ1MzY3ODA5.DtvvnQ.3x4uiFEM5OlXrXeqPuMDBIfOtKY'
DISCORDTOKEN = 'NDcyODUxOTU1ODUzNTU3Nzgw.DuHqow.khRFp2p8vmeWXDVxDTc2loou3tk'
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
    
    if message.channel.id in boundChannels:
        if message.content.lower().startswith('%shello' % PREF):
            msg = 'Hello {0.author.mention}'.format(message)
            await client.send_message(message.channel, msg)
            
        if message.content.lower().startswith('%ssearch' % PREF):
            msg = message.content.lower()
            msgList = msg.split()
            msgList.pop(0)
            
            if msgList == []:
                await client.send_message(message.channel, ':x:** Proper use:** `%ssearch <query>`' % PREF)
                return
            
            msg = ' '.join(msgList)
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
                    
        if message.content.lower().startswith('%screate' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) == True:
                
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%screate <playlist name>`' % PREF)
                    return
                
                msg = ' '.join(msgList)
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
                
        if message.content.lower().startswith('%sdelete' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) == True:
                response = sapi.removePlaylist()
                
                if response == 'Deleted successfully.':
                    await client.send_message(message.channel, response)
                else:
                    await client.send_message(message.channel, response)
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        if message.content.lower().startswith('%splaylist' % PREF):
            response = sapi.getPlaylist()
            await client.send_message(message.channel, response)
            
        if message.content.lower().startswith('%sprefix' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) == True:
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                
                if msgList == []:
                    await client.send_message(message.channel, ':x:** Proper use:** `%sprefix <prefix>`' % PREF)
                    return
                
                msg = ' '.join(msgList)
                PREF = msg
                await client.send_message(message.channel, 'Changed prefix to `%s`' % PREF)
                return PREF
            else:
                await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')
                
        if message.content.lower().startswith('%shelp' % PREF):
            await client.send_message(message.channel, 'Available commands:\n```%sverify - allows you to verify your Spofity account\n%ssearch <query> - searches for a song to add it to playlist\n%splaylist - shows the playlist\n%shelp - shows this help```\nAdditional commands for admins:\n```%screate <name> - creates playlist with name <name>\n%sdelete - deletes playlist\n%sprefix <new prefix> - sets the prefix\n%sbind - binds bot to specified channel (where it accepts commands```\n**NOTE:** Bot only allows for one playlist for now!' % (PREF, PREF, PREF, PREF, PREF, PREF, PREF, PREF))
            
        if message.content.lower().startswith('%sverify' % PREF):
            boundChannels.append(message.author)
            serverObj = client.get_server(client.servers[0])
            memberObj = message.author
            response = sapi.verifyPremiumStep1()
            await client.send_message(message.author, ('To verify the account go to the following page and paste in the token:\n' + response))
            answ = await client.wait_for_message(author=message.author, timeout=60)
            authResponse = sapi.verifyPremiumStep2(answ.content)
            if authResponse == True:
                await client.send_message(message.author, 'You have premium subscription. You just got \'premium\' role')
                role = discord.utils.get(serverObj.roles, name='PREMIUM :star:')
                await client.add_roles(memberObj, role)
            elif authResponse == False:
                await client.send_message(message.author, 'You don\'t have a premium subscribtion')
            else:
                await client.send_message(message.author, authResponse)
            boundChannels.remove(message.author)
        if message.content.lower().startswith('%sdebug' % PREF):
            variable = client
            await asyncio.sleep(5)
    elif message.content.lower().startswith('%sbind' % PREF):
        if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_server) == True:
            if boundChannel == message.channel.id:
                await client.send_message(message.channel, 'Already bound')
            else:
                boundChannel = message.channel.id
                await client.send_message(message.channel, '***Bound to this channel.***')
                return boundChannel
        else:
            await client.send_message(message.channel, ':x:***You are not allowed to execute that command!***')

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    client.

client.loop.create_task(statusChange())
client.run(DISCORDTOKEN)
