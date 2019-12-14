import json
import random
import re
import socket
import ssl
import time


'''
Helper functions
'''

def connect(bot):
    host = 'api.vndb.org'
    port = 19535
    cont = ssl.create_default_context()
    sock = socket.create_connection((host, port))
    bot.sock = cont.wrap_socket(sock, server_hostname=host)
    with open('tokens/vndb', 'rb') as token:
        bot.sock.send(token.read())
    bot.sock.recv(128)


async def receive_data(bot, channel, type):
    # I want to do this loop better
    res = bot.sock.recv(2048)
    while res[-1:] != b'\x04':
        res += bot.sock.recv(2048)

    response, res = res.decode().split(' ', 1)
    res = json.loads(res[:-1])

    if response == 'error' and res['id'] == 'throttled':
        await channel.send('Too many requests. Sleeping for {} seconds.'.format(res['fullwait']))
        time.sleep(res['fullwait'])
        raise Exception

    if type == 'stats':
        return res
    elif not res['num']:
        return None
    elif type == 'relations':
        return res['items'][0]
    elif res['num'] == 1:
        return res['items'][0]
    else:
        return await choose(bot, res, channel, type)


def load_tags(bot):
    with open('data/vndb-tags-2019-12-13.json', 'r') as dump:
        tags = json.load(dump)

    bot.tags, bot.tag_ids = dict(), dict()
    for tag in tags:
        bot.tag_ids[tag['id']] = tag['name']
        for alias in[tag['name']] + tag['aliases']:
            bot.tags[alias.lower()] = tag


def load_traits(bot):
    with open('data/vndb-traits-2019-12-13.json', 'r') as dump:
        traits = json.load(dump)

    bot.traits, bot.trait_ids = dict(), dict()
    for trait in traits:
        bot.trait_ids[trait['id']] = trait['name']
        for alias in[trait['name']] + trait['aliases']:
            bot.traits[alias.lower()] = trait


async def embed_game(bot, data, description, channel, footer=None):
    url = 'https://vndb.org/v{}'.format(data['id'])
    if not footer:
        footer = 'Release date: {}'.format(data['released'])
    if data['original']:
        title = '{} ({})'.format(data['original'], data['title'])
    else:
        title = data['title']
    if not data['image_nsfw']:
        thumbnail = data['image']
    else:
        thumbnail = 'https://i.imgur.com/p8HQTjm.png'

    await bot.post_embed(title=title, description=description, url=url,
        thumbnail=thumbnail, footer=footer, channel=channel)


async def embed_character(bot, data, description, channel, footer=None, thumbnail=None):
    url = 'https://vndb.org/c{}'.format(data['id'])
    if data['original']:
        title = '{} ({})'.format(data['original'], data['name'])
    else:
        title = data['name']
    if footer:
        footer = footer
    image = data['image']
    if thumbnail:
        image = None
        thumbnail = data['image']

    await bot.post_embed(title=title, description=description, url=url,
        image=image, thumbnail=thumbnail, footer=footer, channel=channel)


async def choose(bot, res, channel, type):
    title = 'Which did you mean?'
    description = str()
    if type == 'game':
        key = 'title'
    elif type == 'char':
        key = 'name'

    for i in range(min(9, res['num'])):
        if type == 'char' and res['items'][i]['original']:
            description += '**[{}]** {} ({})\n'.format(i + 1, res['items'][i]['original'], res['items'][i][key])
        else:
            description += '**[{}]** {}\n'.format(i + 1, res['items'][i][key])
    if res['num'] > 9:
        footer = 'Some search results not shown. Refine your search terms to display them.'
    else:
        footer = None
    await bot.post_embed(title=title, description=description, footer=footer, channel=channel)
    msg = await bot.wait_for('message', timeout=10)
    while not msg.channel == channel:
        msg = await bot.wait_for('message', timeout=10)
    index = int(msg.content) - 1
    if not 0 <= index <= min(9, res['num']):
        return None
    return res['items'][index]


'''
General Functions
'''

async def help(bot, channel):
    with open('data/help') as help:
        await bot.post_embed(title='Commands:', description=help.read(), channel=channel)


async def interject(message):
    if random.randint(0, 1):
        msg = "I'd just like to interject for a moment. What you're referring to as _eroge_, is in fact, _erogay_, or as I've recently taken to calling it, ero _plus_ gay."
    else:
        msg = re.sub('eroge', '**erogay**', message.content)
    await message.channel.send(msg)


'''
Game functions
'''

# Search by name, find description
async def search(bot, filter, channel):
    query = bytes('get vn basic,details {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'game')

    if not data:
        await channel.send('Visual novel not found.')
        return
    elif data['description']:
        description = data['description'][:1000] + (data['description'][1000:] and '...')
        description = re.sub('\[.*?[F|f]rom.*]', '', description)
        description = re.sub('\[.*?](.*?)\[/.*?]', '\g<1>', description)
    else:
        description = 'No description.'

    await embed_game(bot, data, description, channel)


# Search by name, find tags
async def get_tags(bot, filter, channel):
    query = bytes('get vn basic,details,tags {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'game')

    if not data:
        await channel.send('Visual novel not found.')
        return
    elif data['tags']:
        description = list()
        for tag in data['tags']:
            if not tag[2]:
                description.append(bot.tag_ids[tag[0]])
            else:
                description.append('||{}||'.format(bot.tag_ids[tag[0]]))
        description = ', '.join(description)
        footer = None
        if len(description) > 1000:
            description = description[:1000].rsplit(', ', 1)[0] + ', ...'
            description += '||' if description.count('||') % 2 else ''
            footer = 'Some tags not shown.'
    else:
        description = 'No tags found.'
        footer = None

    await embed_game(bot, data, description, channel, footer=footer)


# Search by name, find related novels
async def get_relations(bot, filter, channel):
    query = bytes('get vn basic,details,relations {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'relations')

    if not data:
        await channel.send('API Error.')
        return
    
    description = '**Related Visual Novels:**\n\n'
    for r in data['relations']:
        description += r['title'] + '\n'
        description += 'https://vndb.org/v{}'.format(r['id']) + '\n\n'

    await embed_game(bot, data, description, channel)


# Get random novel
async def get_random(bot, channel):
    connect(bot)
    bot.sock.send(b'dbstats\x04')
    data = await receive_data(bot, channel, 'stats')
    filter = '(id = {})'.format(random.randint(1, data['vn']))
    await search(bot, filter, channel)


'''
Tag functions
'''

async def tag_define(bot, args, channel):
    #TODO
    return


async def tag_search(bot, args, channel):
    tags = list()
    for arg in args.lower().split(', '):
        if arg in bot.tags and bot.tags[arg]['searchable']:
            tags.append(bot.tags[arg]['id'])

    if not tags:
        await channel.send('Tag(s) not found')
        return

    filter = '(tags = {})'.format(json.dumps(tags))
    await search(bot, filter, channel)


'''
Character functions
'''

async def search_character(bot, filter, channel):
    query = bytes('get character basic,details {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'char')

    if not data:
        await channel.send('Literally who?')
        return

    if data['description']:
        description = data['description'][:1000] + (data['description'][1000:] and '...')
        description = re.sub('\[[S|s]poiler]|\[/[S|s]poiler]', '||', description)
        description = re.sub('\[.*?[F|f]rom.*]', '', description)
        description = re.sub('\[.*?](.*?)\[/.*?]', '\g<1>', description)
        description += '||' if description.count('||') % 2 else ''
    else:
        description = 'No description.'

    await embed_character(bot, data, description, channel)


async def get_charinfo(bot, filter, channel):
    query = bytes('get character basic,details,meas,voiced,vns {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'char')

    if not data:
        await channel.send('Literally who?')
        return

    description = str()

    if data['aliases']:
        description += '**Aliases:**\n'
        for alias in data['aliases'].splitlines():
            description += '- {}\n'.format(alias)
        description += '\n'

    if data['gender']:
        genders = {'m': 'Male', 'f': 'Female', 'b': 'Both'}
        description += '**Gender:**\n- {}\n\n'.format(genders[data['gender']])

    if data['bloodt']:
        description += '**Blood Type:**\n- {}\n\n'.format(data['bloodt'].upper())

    if data['height'] or data['weight'] or (data['bust'] and data['waist'] and data['hip']):
        description += '**Measurements:**\n'
        if data['height']:
            description += '- {}cm\n'.format(data['height'])
        if data['weight']:
            description += '- {} kg\n'.format(data['weight'])
        if data['bust'] and data['waist'] and data['hip']:
            description += '- {}/{}/{} cm\n'.format(data['bust'], data['waist'], data['hip'])
        description += '\n'

    description += '**Appears in:**\n'
    for vn in data['vns']:
        query = bytes('get vn basic (id = {})\x04'.format(vn[0]), encoding='utf8')
        bot.sock.send(query)
        game = await receive_data(bot, channel, 'game')
        description += '- {}\n'.format(game['title'])
    description += '\n'

    if data['voiced']:
        description += '**Voiced by:**\n'
        seen = set()
        for va in data['voiced']:
            if va['id'] in seen:
                continue
            seen.add(va['id'])
            query = bytes('get staff basic (id = {})\x04'.format(va['aid']), encoding='utf8')
            bot.sock.send(query)
            actor = await receive_data(bot, channel, 'actor')
            if not actor:
                query = bytes('get staff basic (id = {})\x04'.format(va['id']), encoding='utf8')
                bot.sock.send(query)
                actor = await receive_data(bot, channel, 'actor')
            if actor['original']:
                description += '- {} ({})\n'.format(actor['original'], actor['name'])
            else:
                description += '- {}\n'.format(actor['name'])
        description += '\n'

    await embed_character(bot, data, description, channel, thumbnail=True)


async def get_traits(bot, filter, channel):
    query = bytes('get character basic,details,traits {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'char')

    if not data:
        await channel.send('Literally who?')
    elif data['traits']:
        description = list()
        for trait in data['traits']:
            if not trait[1]:
                description.append(bot.trait_ids[trait[0]])
            else:
                description.append('||{}||'.format(bot.trait_ids[trait[0]]))
        description = ', '.join(description)
        footer = None
        if len(description) > 1000:
            description = description[:1000].rsplit(', ', 1)[0] + ', ...'
            description += '||' if description.count('||') % 2 else ''
            footer = 'Some traits not shown.'
    else:
        description = 'No traits found.'
        footer = None

    await embed_character(bot, data, description, channel, footer=footer, thumbnail=True)


'''
Trait functions
'''

async def trait_define(bot, args, channel):
    #TODO
    return


async def trait_search(bot, args, channel):
    traits = list()
    for arg in args.lower().split(', '):
        if arg in bot.traits and bot.traits[arg]['searchable']:
            traits.append(bot.traits[arg]['id'])

    if not traits:
        await channel.send('trait(s) not found')
        return

    filter = '(traits = {})'.format(json.dumps(traits))
    await character_search(bot, filter, channel)
