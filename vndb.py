import json
import random
import re
import socket
import time


'''
Helper functions
'''


def login(bot):
    bot.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bot.sock.connect(('api.vndb.org', 19534))
    with open('tokens/vndb', 'rb') as token:
        bot.sock.send(token.read())
    print(bot.sock.recv(128).decode())


async def create_embed(bot, data, description, channel):
    url = 'https://vndb.org/v{}'.format(data['id'])
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
    index = int(msg.content) - 1
    if not 0 <= index <= min(9, res['num']):
        return None
    return res['items'][index]


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


'''
Commands
'''


async def search(bot, filter, channel, rand=False):
    query = bytes('get vn basic,details {}\x04'.format(filter), encoding='utf8')
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'game')

    if not data:
        await channel.send('Visual novel not found.')
        return
    elif data['description']:
        description = data['description'][:1000] + (data['description'][1000:] and '...')
        description = re.sub('\[[F|f]rom.*]', '', description)
        description = re.sub('\[.*?](.*?)\[/.*?]', '\g<1>', description)
    else:
        description = 'No description.'

    await create_embed(bot, data, description, channel)


async def rand(bot, channel):
    bot.sock.send(b'dbstats\x04')
    data = await receive_data(bot, channel, 'stats')
    filter = '(id = {})'.format(random.randint(1, data['vn']))
    await search(bot, filter, channel)


async def randtag(bot, args, channel):
    with open('data/vndb-tags-2019-09-04.json', 'r') as dump:
        tags = json.load(dump)
    t = next((tag for tag in tags if args in [tag['name'].lower()] + [a.lower() for a in tag['aliases']]), None)

    if not t:
        await channel.send('Tag not found.')
        return
    if not t['searchable']:
        await channel.send('Tag not searchable.')
        return
    filter = '(tags = {})'.format(t['id'])
    await search(bot, filter, channel, rand=True)


async def relations(bot, filter, channel):
    query = bytes('get vn basic,details,relations {}\x04'.format(filter), encoding='utf8')
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'relations')

    if not data:
        await channel.send('API Error.')
        return
    
    description = '**Related Visual Novels:**\n\n'
    for r in data['relations']:
        description += r['title'] + '\n'
        description += 'https://vndb.org/v{}'.format(r['id']) + '\n\n'

    await create_embed(bot, data, description, channel)


async def character(bot, filter, channel):
    query = bytes('get character basic,details {}\x04'.format(filter), encoding='utf8')
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'char')

    if not data:
        await channel.send('Literally who?')
        return
    elif data['original']:
        title = '{} ({})'.format(data['original'], data['name'])
    else:
        title = data['name']

    if data['description']:
        description = data['description'][:1000] + (data['description'][1000:] and '...')
        description = re.sub('\[[S|s]poiler]|\[/[S|s]poiler]', '||', description)
        description = re.sub('\[[F|f]rom.*]', '', description)
        description = re.sub('\[.*?](.*?)\[/.*?]', '\g<1>', description)
        description += '||' if description.count('||') % 2 else ''
    else:
        description = 'No description.'

    url = 'https://vndb.org/c{}'.format(data['id'])
    image = data['image']

    await bot.post_embed(title=title, description=description, url=url, image=image,
        channel=channel)


async def characterinfo(bot, filter, channel):
    query = bytes('get character basic,details,meas,voiced,vns {}\x04'.format(filter), encoding='utf8')
    bot.sock.send(query)
    data = await receive_data(bot, channel, 'char')

    if not data:
        await channel.send('Literally who?')
        return
    elif data['original']:
        title = '{} ({})'.format(data['original'], data['name'])
    else:
        title = data['name']

    description = ''

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
        for va in data['voiced']:
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

    url = 'https://vndb.org/c{}'.format(data['id'])
    thumbnail = data['image']

    await bot.post_embed(title=title, description=description, url=url, thumbnail=thumbnail,
        channel=channel)


async def help(bot, channel):
    with open('data/help') as help:
        await bot.post_embed(title='Commands:', description=help.read(), channel=channel)


async def interject(message):
    if random.randint(0, 1):
        msg = "I'd just like to interject for a moment. What you're referring to as eroge, is in fact, erogay, or as I've recently taken to calling it, ero plus gay."
    else:
        msg = re.sub('eroge', '**erogay**', message.content)
    await message.channel.send(msg)
