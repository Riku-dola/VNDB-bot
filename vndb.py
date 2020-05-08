import json
import bbcode
import random
import re
import socket
import ssl
import time


'''
Helper functions
'''

# Initiate a TCP connection to the VNDB API
# Must be called prior to every request
def connect(bot):
    host = 'api.vndb.org'
    port = 19535
    cont = ssl.create_default_context()
    sock = socket.create_connection((host, port))
    bot.sock = cont.wrap_socket(sock, server_hostname=host)

    # Send credentials to authenticate
    with open('tokens/vndb', 'rb') as token:
        bot.sock.send(token.read())

    # Receive response
    bot.sock.recv(128)


# Read response from the open TCP connection
async def receive_data(bot, channel, author=None, raw=False, jp=False):
    # Read until the End of Transmission character is found
    chunk = 4096  # 4KB
    res = bot.sock.recv(chunk)
    while res[-1:] != b'\x04':
        res += bot.sock.recv(chunk)

    # Parse response
    response, data = res.decode().split(' ', 1)
    data = json.loads(data[:-1])

    # Sleep if API limit has been reached
    if response == 'error' and data['id'] == 'throttled':
        await channel.send('Too many requests. Sleeping for {} seconds.'.format(data['fullwait']))
        time.sleep(data['fullwait'])
        raise Exception

    # For raw data types, return the pure data
    if raw:
        return data
    # If no results found, return None
    elif not data['num']:
        return None
    # If only one result found/desired, return the first one
    elif not author or len(data['items']) == 1:
        return data['items'][0]
    # Otherwise, prompt the user to choose
    else:
        return await choose_prompt(bot, data, channel, author, jp=jp)


# Display a prompt for the user if there are multiple
# options to choose from
async def choose_prompt(bot, data, channel, author, jp=False):
    # Initialise variables for embed
    title = 'Which did you mean?'
    description = str()

    # Choose the correct dict key depending on data type
    key = 'title' if 'title' in data['items'][0].keys() else 'name'

    # Build the list of options
    for i in range(min(9, data['num'])):
        if jp:
            description += '**[{}]** {} ({})\n'.format(i + 1, data['items'][i][key], data['items'][i]['original'])
        else:
            description += '**[{}]** {}\n'.format(i + 1, data['items'][i][key])

    # Initialise the footer based on the number of options
    if data['num'] > 9:
        footer = 'Some search results not shown. Refine your search terms to display them.'
    else:
        footer = None

    # Display the prompt
    await bot.post_embed(title=title, description=description, footer=footer, channel=channel)

    # Ensure responses are not sniped by other users/channel's messages
    def check(m):
        return m.channel == channel and m.author == author

    # Receive the response
    msg = await bot.wait_for('message', check=check, timeout=10)
    index = int(msg.content[0]) - 1

    # Return the chosen object if valid
    if 0 <= index <= min(9, data['num']):
        return data['items'][index]


# Build dicts of tags in memory so that they can be
# 1. Indexed by tag name to find the ID
# 2. Indexed by tag name/alias to find all info
def load_tags(bot):
    # Read the tags data file
    with open('data/vndb-tags-2020-05-07.json', 'r') as dump:
        tags = json.load(dump)

    # Construct the two dicts
    bot.tags, bot.tag_ids = dict(), dict()
    for tag in tags:
        bot.tag_ids[tag['id']] = tag['name']
        for alias in[tag['name']] + tag['aliases']:
            bot.tags[alias.lower()] = tag


# Build dicts of traits in memory so that they can be
# 1. Indexed by tag name to find the ID
# 2. Indexed by tag name/alias to find all info
def load_traits(bot):
    # Read the tags data file
    with open('data/vndb-traits-2020-05-07.json', 'r') as dump:
        traits = json.load(dump)

    # Construct the two dicts
    bot.traits, bot.trait_ids = dict(), dict()
    for trait in traits:
        bot.trait_ids[trait['id']] = trait['name']
        for alias in[trait['name']] + trait['aliases']:
            bot.traits[alias.lower()] = trait


# Format and remove non-plaintext from descriptions
def clean_description(description):
    # Format spoilers
    description = re.sub('\[/?spoiler]', '||', description, flags=re.IGNORECASE)
    # Remove image links
    description = re.sub('\[url=.*?\](NSFW\s)?Example\s?\d*\[\/url\]', '', description, flags=re.IGNORECASE)
    # Strip bbcode
    description = bbcode.Parser().strip(description)
    # Remove sources
    description = re.sub('\[.*?from.*]', '', description, flags=re.IGNORECASE)
    # Strip trailing newlines/spaces
    description = description.rstrip()
    # Trim text to 1000 characters
    description = description[:1000] + (description[1000:] and '...')
    # Restore closing spoiler tag if trimmed
    description += '||' if description.count('||') % 2 else ''
    # Remove extraneous newlines
    description = re.sub(r'\n\s*\n', '\n\n', description)

    return description


# Build an embed based on data from a game dict
async def embed_game(bot, data, description, channel, footer=None):
    url = 'https://vndb.org/v{}'.format(data['id'])
    if not footer:
        footer = 'Release date: {}'.format(data['released'])
    if data['original']:
        title = '{} ({})'.format(data['title'], data['original'])
    else:
        title = data['title']
    if not data['image_nsfw']:
        thumbnail = data['image']
    else:
        thumbnail = 'https://i.imgur.com/p8HQTjm.png'

    await bot.post_embed(title=title, description=description, url=url,
        thumbnail=thumbnail, footer=footer, channel=channel)


# Build an embed based on data from a character dict
async def embed_character(bot, data, description, channel, footer=None, thumbnail=None):
    url = 'https://vndb.org/c{}'.format(data['id'])
    if data['original']:
        title = '{} ({})'.format(data['name'], data['original'])
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


'''
General Functions
'''

async def help(bot, channel):
    with open('data/help-0') as help:
        await bot.post_embed(author='Help:', description=help.read(),
                channel=channel, icon=bot.user.avatar_url)

    def check(m):
        return m.channel == channel and m.author != bot.user

    msg = await bot.wait_for('message', check=check, timeout=10)
    idx = int(msg.content[0])

    if idx == 1:
        with open('data/help-1') as help:
            await bot.post_embed(title='Information:', description=help.read(),
                    channel=channel, thumbnail=bot.user.avatar_url)
    elif idx == 2:
        with open('data/help-2') as help:
            await bot.post_embed(title='Game Commands:', description=help.read(), channel=channel)
    elif idx == 3:
        with open('data/help-3') as help:
            await bot.post_embed(title='Tag Commands:', description=help.read(), channel=channel)
    elif idx == 4:
        with open('data/help-4') as help:
            await bot.post_embed(title='Character Commands:', description=help.read(), channel=channel)
    elif idx == 5:
        with open('data/help-5') as help:
            await bot.post_embed(title='Trait Commands:', description=help.read(), channel=channel)


async def interject(message):
    # Trigger an interjection ~30% of the time
    if random.randint(1, 100) < 30:
        choice = random.randint(1, 3)
        if choice == 1:
            msg = "I'd just like to interject for a moment. What you're referring to as _eroge_, is in fact, _erogay_, or as I've recently taken to calling it, ero _plus_ gay."
        elif choice == 2:
            msg = re.sub('eroge', '**erogay**', message.content)
        elif choice == 3:
            msg = "**BUY LAMUNATION OUT NOW ON STEAM** https://store.steampowered.com/app/1025140/LAMUNATION_international/"
        # Add more choices...

        await message.channel.send(msg)


'''
Game functions
'''

# Search by name, find description
async def search(bot, filter, channel, author=None):
    query = bytes('get vn basic,details {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, author=author)

    if not data:
        await channel.send('Visual novel not found.')
        return
    elif data['description']:
        description = clean_description(data['description'])
    else:
        description = 'No description.'

    await embed_game(bot, data, description, channel)


# Search by name, find tags
async def get_tags(bot, filter, channel, author):
    query = bytes('get vn basic,details,tags {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, author=author)

    if not data:
        await channel.send('Visual novel not found.')
        return
    elif data['tags']:
        description = list()
        for tag in data['tags']:
            try:
                if not tag[2]:
                    description.append(bot.tag_ids[tag[0]])
                else:
                    description.append('||{}||'.format(bot.tag_ids[tag[0]]))
            except KeyError:
                pass
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


# Search by name, find characters
async def get_characters(bot, args, channel, author):
    # Search by VN title to find the ID
    filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
    query = bytes('get vn basic {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    game = await receive_data(bot, channel)

    # Exit if game not found
    if not game:
        await channel.send('Visual novel not found.')
        return

    # Search characters matching game ID
    filter = '(vn = "{}")'.format(game['id'])
    await search_character(bot, filter, channel, author)


# Search by name, find related novels
async def get_relations(bot, filter, channel, author):
    query = bytes('get vn basic,details,relations {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, author)

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
    data = await receive_data(bot, channel, raw=True)
    filter = '(id = {})'.format(random.randint(1, data['vn']))
    await search(bot, filter, channel)


'''
Tag functions
'''

async def tag_define(bot, args, channel):
    try:
        title = bot.tags[args]['name']
        description = clean_description(bot.tags[args]['description'])
        url = 'https://vndb.org/g{}'.format(bot.tags[args]['id'])
        footer = 'Aliases: {}'.format(', '.join(bot.tags[args]['aliases'])) if bot.tags[args]['aliases'] else None
        await bot.post_embed(title=title, description=description, url=url, channel=channel, footer=footer)
    except KeyError:
        await channel.send('Tag not found.')


async def tag_search(bot, args, channel, author):
    tags = list()
    for arg in args.lower().split(', '):
        if arg in bot.tags and bot.tags[arg]['searchable']:
            tags.append('tags = [{}]'.format(bot.tags[arg]['id']))

    if not tags:
        await channel.send('Tag(s) not found.')
        return

    filter = '({})'.format(' and '.join(tags))
    await search(bot, filter, channel, author=author)


'''
Character functions
'''

async def search_character(bot, filter, channel, author):
    query = bytes('get character basic,details {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, author=author, jp=True)

    if not data:
        await channel.send('Literally who?')
        return

    if data['description']:
        description = clean_description(data['description'])
    else:
        description = 'No description.'

    await embed_character(bot, data, description, channel)


async def get_charinfo(bot, filter, channel, author):
    query = bytes('get character basic,details,meas,voiced,vns {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, author=author, jp=True)

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
        game = await receive_data(bot, channel)
        description += '- {}\n'.format(game['title'])
    description += '\n'

    if data['voiced']:
        description += '**Voiced by:**\n'
        seen = set()
        for va in data['voiced']:
            if va['id'] in seen:
                continue
            seen.add(va['id'])
            query = bytes('get staff basic,aliases (id = {})\x04'.format(va['id']), encoding='utf8')
            bot.sock.send(query)
            actor = await receive_data(bot, channel)
            aliases = {alias[0]:alias for alias in actor['aliases']}
            alias = aliases[va['aid']]
            if alias[2]:
                description += '- {} ({})\n'.format(alias[1], alias[2])
            # Might be unnecessary to handle this case
            else:
                description += '- {}\n'.format(alias[1])
        description += '\n'

    await embed_character(bot, data, description, channel, thumbnail=True)


async def get_traits(bot, filter, channel, author):
    query = bytes('get character basic,details,traits {}\x04'.format(filter), encoding='utf8')
    connect(bot)
    bot.sock.send(query)
    data = await receive_data(bot, channel, author=author, jp=True)

    if not data:
        await channel.send('Literally who?')
    elif data['traits']:
        description = list()
        for trait in data['traits']:
            try:
                if not trait[1]:
                    description.append(bot.trait_ids[trait[0]])
                else:
                    description.append('||{}||'.format(bot.trait_ids[trait[0]]))
            except KeyError:
                pass
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
    try:
        title = bot.traits[args]['name']
        description = clean_description(bot.traits[args]['description'])
        url = 'https://vndb.org/i{}'.format(bot.traits[args]['id'])
        footer = 'Aliases: {}'.format(', '.join(bot.traits[args]['aliases'])) if bot.traits[args]['aliases'] else None
        await bot.post_embed(title=title, description=description, url=url, channel=channel, footer=footer)
    except KeyError:
        await channel.send('Trait not found.')


async def trait_search(bot, args, channel, author):
    traits = list()
    for arg in args.lower().split(', '):
        if arg in bot.traits and bot.traits[arg]['searchable']:
            traits.append('traits = [{}]'.format(bot.traits[arg]['id']))

    if not traits:
        await channel.send('Trait(s) not found.')
        return

    filter = '({})'.format(' and '.join(traits))
    await search_character(bot, filter, channel, author)
