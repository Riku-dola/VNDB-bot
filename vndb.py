import json
import random
import re
import socket
import textwrap


def login(bot):
    bot.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bot.sock.connect(('api.vndb.org', 19534))
    with open('tokens/vndb', 'rb') as token:
        bot.sock.send(token.read())
    print(bot.sock.recv(128))


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


async def choose(bot, res, channel, game):
    title = 'Which did you mean?'
    description = str()
    key = 'title' if game else 'name'
    for i in range(min(9, res['num'])):
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


async def search(bot, filter, channel, rand=False):
    query = bytes('get vn basic,details {}\x04'.format(filter), encoding='utf8')
    bot.sock.send(query)
    # I want to do this loop better
    res = bot.sock.recv(2048)
    while res[-1:] != b'\x04':
        res += bot.sock.recv(2048)

    # more elegant way to do this?
    res = json.loads(res.decode()[8:-1])
    # print(json.dumps(res, sort_keys=True, indent=4, separators=(',', ': ')))
    if not res['num']:
        await channel.send('Visual novel not found.')
        return
    elif rand:
        data = res['items'][random.randint(0, len(res['items']) - 1)]
    elif res['num'] == 1:
        data = res['items'][0]
    else:
        data = await choose(bot, res, channel, True)

    if not data:
        print('early exit') 
        return
    elif data['description']:
        description = textwrap.shorten(data['description'], width=1000, placeholder='...')
        description = re.sub('\[From.*]', '', description)
        description = re.sub('\[.*?](.*?)\[/.*?]', '\g<1>', description)
    else:
        description = 'No description.'

    await create_embed(bot, data, description, channel)


async def rand(bot, channel):
    bot.sock.send(b'dbstats\x04')
    stats = json.loads(bot.sock.recv(256).decode()[8:-1])
    filter = '(id = {})'.format(random.randint(1, stats['vn']))
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
    # I want to do this loop better
    res = bot.sock.recv(2048)
    while res[-1:] != b'\x04':
        res += bot.sock.recv(2048)

    try:
        res = json.loads(res.decode()[8:-1])
        description = '**Related Visual Novels:**\n\n'
        for r in res['items'][0]['relations']:
            description += r['title'] + '\n'
            description += 'https://vndb.org/v' + r['id'] + '\n\n'

        await create_embed(bot, res, description, channel)

    except:
        await channel.send('API Error.')


async def character(bot, filter, channel):
    query = bytes('get character basic,details,voiced,vns {}\x04'.format(filter), encoding='utf8')
    bot.sock.send(query)
    # I want to do this loop better
    res = bot.sock.recv(2048)
    while res[-1:] != b'\x04':
        res += bot.sock.recv(2048)

    print(res.decode())
    res = json.loads(res.decode()[8:-1])
    if not res['num']:
        await channel.send('Character not found.')
        return
    elif res['num'] == 1:
        data = res['items'][0]
    else:
        data = await choose(bot, res, channel, False)

    title = '{} ({})'.format(data['original'], data['name'])
    if data['description']:
        description = textwrap.shorten(data['description'], width=1000, placeholder='...')
        description = re.sub('\[Spoiler]|\[/Spoiler]', '||', description)
    else:
        description = 'No description.'
    url = 'https://vndb.org/c{}'.format(data['id'])
    image = data['image']

    await bot.post_embed(title=title, description=description, url=url, image=image,
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
