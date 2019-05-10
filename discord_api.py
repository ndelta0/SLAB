import asyncio
import logging
import os
import signal
import threading
import colorama
import discord
import mysql.connector
import _datetime
from spotify_api import *

colorama.init(autoreset=True)
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


# Variables & classes
class MyFormatter(logging.Formatter):
    info_fmt = ('%(name)s || %(levelname)s: %(message)s')
    warn_fmt = ('\033[36m%(name)s || %(levelname)s: %(message)s')
    err_fmt = ('\033[33m%(name)s || %(levelname)s: %(message)s')
    crit_fmt = ('\033[31m%(name)s || %(levelname)s: %(message)s')
    def __init__(self):
        super().__init__(fmt='%(levelno)d: %(msg)s', datefmt=None, style='%')
    def format(self, record):
        format_orig = self._style._fmt
        if record.levelno == logging.INFO:
            self._style._fmt = MyFormatter.info_fmt
        elif record.levelno == logging.WARNING:
            self._style._fmt = MyFormatter.warn_fmt
        elif record.levelno == logging.ERROR:
            self._style._fmt = MyFormatter.err_fmt
        elif record.levelno == logging.CRITICAL:
            self._style._fmt = MyFormatter.crit_fmt
        result = logging.Formatter.format(self, record)
        self._style_fmt = format_orig
        return result
stopCode = False
formInst = MyFormatter()
logger = logging.getLogger('DiscordAPI')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formInst)
logger.addHandler(ch)
PREF = settingsDict['prefix']
boundChannels = settingsDict['boundChannels']
DISCORDTOKEN = settingsDict['discordToken']
clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
# <----->

client = discord.Client()


async def statusChange():
    global statusRun
    suffix = os.environ.get('bot-build', 'n/d')
    await client.wait_until_ready()
    botVersion = os.environ.get('botVersion', 'n/d')
    while 1:
        try:
            await client.wait_until_ready()
            # version
            a = discord.Activity()
            a.application_id = 1
            a.name = 'Version {}{}'.format(botVersion, '-'+suffix)
            a.type = discord.ActivityType.playing

            await client.change_presence(status=discord.Status.online, activity=a)
            await asyncio.sleep(15)

            # help
            b = discord.Activity()
            b.application_id = 1
            b.name = '{}help for help!'.format(PREF)
            b.type = discord.ActivityType.listening

            await client.change_presence(status=discord.Status.online, activity=b)
            await asyncio.sleep(15)
        except BaseException as err:
            logger.critical('Exception occurred (status change): {} '.format(err))
            break

async def muteCheck():
    await client.wait_until_ready()
    guildObj = client.get_guild(408958645745745942)
    role = guildObj.get_role(409001540842422292)
    while 1:
        sql = "SELECT * FROM users WHERE muted = 1"
        try:
            botCursor.execute(sql)
        except BaseException as err:
            logger.info('Exception occurred while unmuting: {}'.format(err))
            database.reconnect(100)
            botCursor.execute(sql)
        muted = botCursor.fetchall()
        if muted != []:
            operations = []
            for member in muted:
                if member[7]-_datetime.datetime.now()<_datetime.timedelta():
                    user = guildObj.get_member(int(member[1]))
                    await user.remove_roles(role, reason='Sentence finished')
                    await user.send('Your sentence has finished. You may now chat in the server.')
                    sql = "UPDATE users SET mute_end = NULL, muted = 0 WHERE id = {}".format(member[0])
                    try:
                        botCursor.execute(sql)
                        database.commit()
                    except BaseException as err:
                        logger.critical('Exception occurred: {} '.format(err))
                        database.reconnect(100)
                        botCursor.execute(sql)
                        database.commit()
        await asyncio.sleep(300)

async def subCheck():
    await client.wait_until_ready()
    guildObj = client.get_guild(408958645745745942)
    role = guildObj.get_role(408976689625038848)
    while 1:
        sql = "SELECT * FROM users WHERE has_tokens = 1"
        try:
            botCursor.execute(sql)
        except BaseException as err:
            logger.info('Exception occured while checking subscription: {}'.format(err))
            database.reconnect(100)
            botCursor.execute(sql)
        users = botCursor.fetchall()
        if users != []:
            for user in users:
                hasPremium = checkSubscription(user[5])
                if not hasPremium:
                    member = guildObj.get_member(int(user[1]))
                    await member.remove_roles(role, reason='Doesn\'t have premium subscription')
                    sql = "UPDATE users SET premium = 0 WHERE id = {}".format(member[0])
                    try:
                        botCursor.execute(sql)
                        database.commit()
                    except BaseException as err:
                        logger.critical('Exception occurred: {} '.format(err))
                        database.reconnect(100)
                        botCursor.execute(sql)
                        database.commit()
        await asyncio.sleep(86400)

@client.event
async def on_message(message):
    global PREF
    global boundChannels

    if message.author == client.user:
        return
    if message.author.bot:
        return

    if message.content.lower().startswith('%sbind' % PREF):
        logger.info(
            ('Received command > bind | From {0.author} in {0.guild.name}/{0.channel}'.format(message)))
        if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:
            if message.channel.id in boundChannels:
                await message.channel.send('Already bound')
            else:
                boundChannels.append(message.channel.id)
                await dbUpdateSettings(
                    ['boundChannels', ' '.join(boundChannels)])
                await message.channel.send('***Bound to this channel.***')
                return boundChannels
        else:
            await message.channel.send(':x:***You are not allowed to execute that command!***')

    if message.content.lower().startswith('%sunbind' % PREF):
        logger.info((
            'Received command > unbind | From {0.author} in {0.guild.name}/{0.channel}'.format(message)))
        if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:
            if message.channel.id not in boundChannels:
                await message.channel.send('Not binded')
            else:
                boundChannels.remove(message.channel.id)
                await dbUpdateSettings(['boundChannels', ' '.join([str(chid) for chid in boundChannels])])
                await message.channel.send('***Unbound from this channel.***')
                return boundChannels
        else:
            await message.channel.send(':x:***You are not allowed to execute that command!***')

    elif message.channel.id in boundChannels:
        if message.content.lower().startswith('%ssearch' % PREF):
            msg = message.content
            msgList = msg.split()
            msgList.pop(0)

            if msgList == []:
                await message.channel.send(':x:** Proper use:** `%ssearch <query/song URI>`' % PREF)
                return

            msg = ' '.join(msgList)
            logger.info(('Received command > search >> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, msg)))
            # await message.channel.send(msg)
            response = await searchSong(msg)

            if response[0] == 1:
                await message.channel.send('Something went wrong. Try again.')

            elif response[0] == 2:
                await message.channel.send('No results.')

            elif response[0] == 3:
                await message.channel.send('Invalid URI. Try copying/pasting it again.')

            elif response[0] == 4:
                await message.channel.send('No track with that URI. Try copying/pasting it again.')

            elif response[0] == 0:
                await message.channel.send('Is this the song you are looking for?')
                await message.channel.send(response[1])
                await message.channel.send('If yes, type `{0}yes <playlist\'s name>` to add to playlist or `{0}no` to cancel'.format(PREF))

                def agreement(m):
                    if not m:
                        return('timeout')
                    elif m.author == message.author:
                        if m.content.lower().startswith('%syes' % PREF):
                            return('yes')
                    return('no')

                ans = await client.wait_for('message', check=agreement, timeout=30)

                if ans.content.lower().startswith('{}yes'.format(PREF)):
                    plName = ' '.join(ans.content.split()[1:])
                    admin = False
                    if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True: admin = True
                    addResp = await addToPlaylist(plName, response[2], str(message.author.id), admin)
                    if addResp[0] == 0:
                        await message.channel.send('Successfully added to playlist `{}`'.format(plName))
                    elif addResp[0] == 1:
                        await message.channel.send('Unable to add to playlist `{}`'.format(plName))
                    elif addResp[0] == 2:
                        await message.channel.send('No playlist named `{}` or no playlists'.format(plName))
                    elif addResp[0] == 3:
                        await message.channel.send('You already done your part creating the playlist')
                elif ans.content.lower().startswith('{}no'.format(PREF)):
                    await message.channel.send('Cancelled.')

        elif message.content.lower().startswith('%screateplaylist' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:

                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)

                if msgList == []:
                    await message.channel.send(':x:** Proper use:** `%screateplaylist <playlist name>`' % PREF)
                    return

                msg = ' '.join(msgList)
                logger.info(
                    ('Received command > create >> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, msg)))
                response = await createPlaylist(msg)

                if response[0] == 1:
                    await message.channel.send('Error creating playlist.')

                elif response[0] == 2:
                    await message.channel.send('Playlist with that name already exists.')

                elif response[0] == 3:
                    await message.channel.send('Invalid character(s). Remove or replace any non-ascii characters.')

                elif response[0] == 0:
                    await message.channel.send('Successfully created playlist `{}`'.format(msg))
                    await message.channel.send(response[1])
            else:
                await message.channel.send(':x:***You are not allowed to execute that command!***')

        elif message.content.lower().startswith('%sdeleteplaylist' % PREF):
            msg = message.content.lower()
            msgList = msg.split()
            msgList.pop(0)

            if msgList == []:
                await message.channel.send(':x:** Proper use:** `%sdeleteplaylist <playlist name>`' % PREF)
                return

            msg = ' '.join(msgList)
            logger.info(
                ('Received command > delete >> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, msg)))
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:

                response = await removePlaylist(msg)

                if response[0] == 1:
                    await message.channel.send('Error deleting playlist.')

                elif response[0] == 2:
                    await message.channel.send('No playlist with that name.')

                elif response[0] == 3:
                    await message.channel.send('Invalid character(s). Remove or replace any non-ascii characters.')

                elif response[0] == 0:
                    await message.channel.send('Successfully deleted playlist `{}`'.format(msg))
            else:
                await message.channel.send(':x:***You are not allowed to execute that command!***')

        elif message.content.lower().startswith('%splaylists' % PREF):
            logger.info(
                ('Received command > playlists | From {0.author} in {0.guild.name}/{0.channel}'.format(message)))
            response = await getPlaylists()
            if response[0] == 1:
                await message.channel.send('Error getting playlists.')
            if response[0] == 2:
                await message.channel.send('No playlists.')
            elif response[0] == 0:
                user = await client.fetch_user(312223735505747968)
                playlistsEmbed = discord.Embed(color=discord.Color.green())
                playlistsEmbed.set_author(
                    name='SLAB playlists', icon_url=client.user.avatar_url)
                for item in response[1]:
                    playlistsEmbed.add_field(
                        name=item[0], value=item[1], inline=True)
                playlistsEmbed.set_footer(text='Made with 💖 by {}'.format(str(user)), icon_url=user.avatar_url)
                await message.channel.send(embed=playlistsEmbed)

        elif message.content.lower().startswith('%sprefix' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)

                if msgList == []:
                    await message.channel.send(':x:** Proper use:** `%sprefix <prefix>`' % PREF)
                    return

                msg = ' '.join(msgList)
                logger.info(
                    ('Received command > prefix >> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, msg)))
                PREF = msg
                await message.channel.send('Changed prefix to `%s`' % PREF)
                await dbUpdateSettings((['prefix', PREF]))
                return PREF

            await message.channel.send(':x:***You are not allowed to execute that command!***')

        elif message.content.lower().startswith('%shelp' % PREF):
            logger.info(
                ('Received command > help | From {0.author} in {0.guild.name}/{0.channel}'.format(message)))
            user = await client.fetch_user(312223735505747968)
            helpEmbed = discord.Embed(
                color=discord.Color.green()
            )
            helpEmbed.set_author(
                name='SLAB Help', icon_url=client.user.avatar_url)
            helpEmbed.add_field(name='%shelp' %
                                PREF, value='Shows this help', inline=True)
            helpEmbed.add_field(
                name='%sverify' % PREF, value='Allows you to obtain Premium:star: role', inline=False)
            helpEmbed.add_field(name='%ssearch <query>' % PREF,
                                value='Allows you to search for a song to add to playlist', inline=True)
            helpEmbed.add_field(name='%sdelete <uri> <playlist>' % PREF,
                                value='Deletes song with <uri> from <playlist>', inline=True)
            helpEmbed.add_field(
                name='%splaylists' % PREF, value='Shows list of available playlists', inline=True)
            helpEmbed.add_field(name='%splaylist <name>' % PREF,
                                value='Shows the requested playlist', inline=True)
            helpEmbed.add_field(name='%screateplaylist <name>' % PREF,
                                value='Creates playlist with name <name>', inline=True)
            helpEmbed.add_field(name='%sdeleteplaylist <name>' % PREF,
                                value='Deletes playlist with name <name>', inline=True)
            helpEmbed.add_field(name='%sprefix <prefix>' % PREF,
                                value='Sets new <prefix> for commands', inline=True)
            helpEmbed.add_field(
                name='%sbind' % PREF, value='Binds bot to current channel', inline=True)
            helpEmbed.add_field(
                name='%sunbind' % PREF, value='Unbinds bot from current channel', inline=True)
            helpEmbed.add_field(
                name='%sclear <number>'%PREF, value='Clears number of messages in current channel', inline=True)
            helpEmbed.add_field(
                name='%swarn <@user>'%PREF, value='Warns mentioned user (warn -> 30 minutes mute -> 1 week mute -> permament mute)', inline=True)
            helpEmbed.add_field(
                name='%swarn-reset <@user>'%PREF, value='Resets number of times user was muted', inline=True)
            helpEmbed.add_field(
                name='%spardon <@user>'%PREF, value='Unmutes mentioned user', inline=True)
            helpEmbed.set_footer(text='Made with 💖 by {}'.format(
                str(user)), icon_url=user.avatar_url)
            await message.channel.send(embed=helpEmbed)

        elif message.content.lower().startswith('%sverify' % PREF):
            logger.info(
                ('Received command > verify | From {0.author} in {0.guild.name}/{0.channel}'.format(message)))
            response = await verifyPremiumStep1(message.author.id)
            await message.author.send(('To verify the account go to the following page and log in (yup, I know that it\'s long and suspicious, but trust me, it\'s a link to Spotify page):\n' + response))

        elif message.content.lower().startswith('%sdelete' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:
                msg = message.content
                msgList = msg.split()
                msgList.pop(0)

                if msgList == []:
                    await message.channel.send(':x:** Proper use:** `%sdelete <song URI> <playlist name>`' % PREF)
                    return

                playlistName = ' '.join(msgList[1:])
                logger.info(('Received command > delete >> {1} - {2} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, msgList[0], playlistName)))
                response = await removeSong(msgList[0], playlistName)

                if response[0] == 1:
                    await message.channel.send('Error deleting song.')
                elif response[0] == 2:
                    await message.channel.send('No playlists')
                elif response[0] == 3:
                    await message.channel.send('Invalid character(s). Remove or replace any non-ascii characters.')
                elif response[0] == 4:
                    await message.channel.send('No playlists with name `{}`'.format(msg[0]))
                elif response[0] == 0:
                    await message.channel.send('Song successfully removed.')
            else:
                await message.channel.send(':x:***You are not allowed to execute that command!***')

        elif message.content.lower().startswith('%splaylist' % PREF):
            msg = message.content.lower()
            msgList = msg.split()
            msgList.pop(0)

            if msgList == []:
                await message.channel.send(':x:** Proper use:** `%splaylist <playlist\'s name>`' % PREF)
                return

            msg = ' '.join(msgList)
            logger.info(
                ('Received command > playlist >> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, msg)))

            response = await getPlaylist(msg)

            if response[0] == 1:
                await message.channel.send('No playlist with name `{}`'.format(msg))
            elif response[0] == 2:
                await message.channel.send('No playlists.')
            elif response[0] == 3:
                await message.channel.send('Invalid character(s). Remove or replace any non-ascii characters.')
            elif response[0] == 0:
                await message.channel.send(response[1])

        elif message.content.lower().startswith('%sclear' % PREF):
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:
                msg = message.content.lower()
                msgList = msg.split()
                msgList.pop(0)
                if msgList == []:
                    return
                limit = int(msgList[0])
                limit += 1
                limit = clamp(n=limit, minn=2, maxn=100)
                channel = message.channel
                messages = await channel.history(limit=limit).flatten()
                await channel.delete_messages(messages)

        elif message.content.lower().startswith('%sdb-update' % PREF):
            logger.info(('Received command > db-update | From {0.author} in {0.guild.name}/{0.channel}'.format(message)))
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.manage_channels or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or (message.author.id == 312223735505747968) == True:
                members_updt = []
                for member in message.guild.members:
                    if not member.bot:
                        data = {'discordid': member.id, 'username': member.name+'#'+member.discriminator, 'warn_times': 0}
                        premium = {'premium': False}
                        if discord.utils.get(client.guilds[0].roles, name='PREMIUM ⭐') in member.roles:
                            premium['premium'] = True
                        data.update(premium)
                        sql = "INSERT INTO users (discordid, username, premium, warn_times) VALUES ('%s', '%s', %s, %s)" % (str(data['discordid']), data['username'], data['premium'], data['warn_times'])
                        try:
                            botCursor.execute(sql)
                            database.commit()
                        except BaseException as err:
                            logger.critical('Exception occurred: {} '.format(err))
                            database.reconnect(100)
                            botCursor.execute(sql)
                            database.commit()
                        members_updt.append(member.name+'#'+member.discriminator)
                await message.channel.send('Users inserted: {} - {}'.format(len(members_updt), ', '.join(members_updt)))

        elif message.content.lower().startswith('%swarn' % PREF):
            logger.info(('Received command > warn >> warned -> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, str(message.mentions[0]))))
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.kick_members or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or message.author.roles[len(message.author.roles)-1].permissions.mute_members or (message.author.id == 312223735505747968) == True:
                warned = message.mentions[0]
                sql = 'SELECT * FROM users WHERE discordid = \'{}\''.format(str(warned.id))
                try:
                    botCursor.execute(sql)
                except BaseException as err:
                    logger.critical('Exception occurred: {} '.format(err))
                    database.reconnect(100)
                    botCursor.execute(sql)
                select = botCursor.fetchone()
                if select[6] == 0:
                    sql = 'UPDATE users SET warn_times = 1 WHERE discordid = \'{}\''.format(str(warned.id))
                    try:
                        botCursor.execute(sql)
                        database.commit()
                    except BaseException as err:
                        logger.critical('Exception occurred: {} '.format(err))
                        database.reconnect(100)
                        botCursor.execute(sql)
                        database.commit()
                    await message.channel.send('Watch out {}! It\'s your first warning. No punishment this time buddy.'.format(warned.mention))
                elif select[6] == 1:
                    sql = 'UPDATE users SET warn_times = 2, muted = True, mute_end = \'{}\' WHERE discordid = \'{}\''.format(_datetime.datetime.now()+_datetime.timedelta(minutes=30), warned.id)
                    try:
                        botCursor.execute(sql)
                        database.commit()
                    except BaseException as err:
                        logger.critical('Exception occurred: {} '.format(err))
                        database.reconnect(100)
                        botCursor.execute(sql)
                        database.commit()
                    role = discord.utils.get(message.guild.roles, name='Muted')
                    await warned.add_roles(role, reason='Member muted for 30 minutes')
                    await message.channel.send('Hey there {}! I\'m sorry to say this, but I muted you for **30 minutes**. If you think that is wrong, contact an administrator directly.'.format(warned.mention))
                elif select[6] == 2:
                    sql = 'UPDATE users SET warn_times = 3, muted = True, mute_end = \'{}\' WHERE discordid = \'{}\''.format(_datetime.datetime.now()+_datetime.timedelta(weeks=1), warned.id)
                    try:
                        botCursor.execute(sql)
                        database.commit()
                    except BaseException as err:
                        logger.critical('Exception occurred: {} '.format(err))
                        database.reconnect(100)
                        botCursor.execute(sql)
                        database.commit()
                    role = discord.utils.get(message.guild.roles, name='Muted')
                    await warned.add_roles(role, reason='Member muted for 1 week')
                    await message.channel.send('Oi mate {}! I\'m sad to say this, but you have been muted for **1 week**. If you think that is wrong, contact an administrator directly.'.format(warned.mention))
                elif select[6] == 3:
                    sql = 'UPDATE users SET warn_times = 4, muted = True, mute_end = \'{}\' WHERE discordid = \'{}\''.format(_datetime.datetime.now()+_datetime.timedelta(days=3652, hours=12), warned.id)
                    try:
                        botCursor.execute(sql)
                        database.commit()
                    except BaseException as err:
                        logger.critical('Exception occurred: {} '.format(err))
                        database.reconnect(100)
                        botCursor.execute(sql)
                        database.commit()
                    role = discord.utils.get(message.guild.roles, name='Muted')
                    await warned.add_roles(role, reason='Member muted permamently')
                    await message.channel.send('That\'s it {}! I\'m really sad to say this, but you have been muted permamently (not permamently, **10 years** tho). If you think that is wrong, contact an administrator directly.'.format(warned.mention))

        elif message.content.lower().startswith('%swarn-reset' % PREF):
            logger.info(('Received command > warn-reset >> warned -> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, str(message.mentions[0]))))
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.kick_members or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or message.author.roles[len(message.author.roles)-1].permissions.mute_members or (message.author.id == 312223735505747968) == True:
                warned = message.mentions[0]
                sql = 'UPDATE users SET warn_times=0, mute_end=NULL, muted=0 WHERE discordid = \'{}\''.format(str(warned.id))
                try:
                    botCursor.execute(sql)
                    database.commit()
                except BaseException as err:
                    logger.critical('Exception occurred: {} '.format(err))
                    database.reconnect(100)
                    botCursor.execute(sql)
                    database.commit()

        elif message.content.lower().startswith('%spardon' % PREF):
            logger.info(('Received command > pardon >> pardoned -> {1} | From {0.author} in {0.guild.name}/{0.channel}'.format(message, str(message.mentions[0]))))
            if (message.author.roles[len(message.author.roles)-1].permissions.administrator or message.author.roles[len(message.author.roles)-1].permissions.kick_members or message.author.roles[len(message.author.roles)-1].permissions.manage_guild) or message.author.roles[len(message.author.roles)-1].permissions.mute_members or (message.author.id == 312223735505747968) == True:
                pardoned = message.mentions[0]
                sql = 'SELECT * FROM users WHERE discordid = \'{}\''.format(str(pardoned.id))
                try:
                    botCursor.execute(sql)
                except BaseException as err:
                    logger.critical('Exception occurred: {} '.format(err))
                    database.reconnect(100)
                    botCursor.execute(sql)
                    select = botCursor.fetchone()
                    if select[8] == 0:
                        await message.channel.send('This user is not muted.')
                    else:
                        guildObj = client.get_guild(454888283927871508)
                        role = guildObj.get_role(574186709382856714)
                        await pardoned.remove_roles(role, reason='Sentence finished')
                        await pardoned.send('Your sentence has finished. You may now chat in the server.')
                        sql = "UPDATE users SET mute_end = NULL, muted = 0 WHERE id = {}".format(select[0])
                        try:
                            botCursor.execute(sql)
                            database.commit()
                        except BaseException as err:
                            logger.critical('Exception occurred: {} '.format(err))
                            database.reconnect(100)
                            botCursor.execute(sql)
                            database.commit()
                        await message.channel.send('You have forgiven {} for his offences.')

@client.event
async def on_ready():
    logger.info(('Logging in as:'))
    logger.info((client.user.name))
    logger.info((client.user.id))
    logger.info(('------'))

@client.event
async def on_resumed():
    logger.info('Reconnected')

@client.event
async def on_member_update(bef, aft):
    if 408991159990616074 in [y.id for y in bef.roles]:
        if 408991159990616074 not in [y.id for y in aft.roles]:
            await client.get_channel(516168648373698563).send(discord.Object(id=409023617549205515), '{0}, if you want to obtain PREMIUM ⭐ role, type in `{1}verify` in {2}'.format(aft.mention, PREF, client.get_channel(516168648373698563).mention))

@client.event
async def on_member_join(member):
    sql = "SELECT * FROM users WHERE discordid = '{}'".format(str(member.id))
    try:
        botCursor.execute(sql)
    except BaseException as err:
        logger.critical('Exception occurred: {} '.format(err))
        database.reconnect(100)
        botCursor.execute(sql)
    if not botCursor.fetchone():
        data = {'discordid': member.id, 'username': member.name+'#'+member.discriminator, 'warn_times': 0, 'premium': False}
        sql = "INSERT INTO users (discordid, username, premium, warn_times, muted) VALUES ('%s', '%s', %s, %s, 0)" % (str(data['discordid']), data['username'], data['premium'], data['warn_times'])
        try:
            botCursor.execute(sql)
            database.commit()
        except BaseException as err:
            logger.critical('Exception occurred: {} '.format(err))
            database.reconnect(100)
            botCursor.execute(sql)
            database.commit()

if __name__ == "__main__":
    logger.info(('Starting code...'))

    loop = asyncio.get_event_loop()
    loop.create_task(statusChange())
    loop.create_task(muteCheck())
    loop.create_task(subCheck())

    while True:
        try:
            client.loop.run_until_complete(client.start(DISCORDTOKEN))
        except SystemExit as err:
            logger.info('Stopping code... (SystemExit)')
            stopCode = True
            client.logout()
            logger.info('Stopped code')
        except KeyboardInterrupt as err:
            logger.info('Stopping code... (KeyboardInterrupt)')
            stopCode = True
            client.logout()
            logger.info('Stopped code')
        except RuntimeError as err:
            logger.critical('Exception occurred: {} '.format(err))
            client.close()
        except Exception as err:
            logger.critical('Exception occurred: {} '.format(err))
            logger.info('Trying to reconnect...')
            client.logout()
        if stopCode:
            break
    exit(0)
