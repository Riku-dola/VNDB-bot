import discord, vndb

class vndbot(discord.Client):
    async def on_ready(self):
        print('connected')


    async def on_connect(self):
        vndb.load_tags(self)
        vndb.load_traits(self)


    async def on_disconnect(self):
        self.sock.close()


    async def post_embed(self, color=0x2D2D2D, title=None, description=None, url=None,
            author=None, icon=None, thumbnail=None, image=None, footer=None, channel=None):
        embed = discord.Embed(color=color, title=title, description=description, url=url)
        if author and icon:
            embed.set_author(name=author, url=discord.Embed.Empty, icon_url=icon)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if image:
            embed.set_image(url=image)
        if footer:
            embed.set_footer(text=footer)
        await channel.send(embed=embed)


    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content == '.reconnect' and message.author.id == 138581816872271872:
            vndb.connect(self)
            await message.channel.send('Successfully reconnected.')
            return

        if 'eroge' in message.content.lower():
            await vndb.interject(message)

        if not message.content.startswith('.vn '):
            return

        _, cmd, *args = message.content.lower().split(' ', 2)
        args = args[0] if args else None
        channel = message.channel
        author = message.author

        aliases = ['help', 'h']
        if cmd in aliases:
            await vndb.help(self, channel)
            return


        '''
        Game commands
        '''

        aliases = ['search', 's', 'find', 'f']
        # Search by name, find description
        if cmd in aliases:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.search(self, filter, channel, author=author)
            return

        aliases = ['gettags', 'gt']
        # Search by name, find tags
        if cmd in aliases:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_tags(self, filter, channel, author)
            return

        aliases = ['getcharacters', 'getchars', 'gc']
        # Search by name, find related novels
        if cmd in aliases:
            await vndb.get_characters(self, args, channel, author)
            return

        aliases = ['getrelations', 'getrelated', 'gr', 'relations', 'related', 'rel']
        # Search by name, find related novels
        if cmd in aliases:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_relations(self, filter, channel, author)
            return

        aliases = ['random', 'rand', 'r']
        # Get random novel
        if cmd in aliases:
            await vndb.get_random(self, channel)
            return


        '''
        Tag commands
        '''

        aliases = ['tagdefine', 'td']
        # Search by tag, get definition
        if cmd in aliases:
            await vndb.tag_define(self, args, channel)
            return

        aliases = ['tagsearch', 'ts']
        # Search by tag, get novels
        if cmd in aliases:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.tag_search(self, filter, channel, author)
            return


        '''
        Character commands
        '''

        aliases = ['character', 'char', 'c']
        # Search by name, get description
        if cmd in aliases:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.search_character(self, filter, channel, author)
            return

        aliases = ['getcharinfo', 'charinfo', 'gci', 'gi']
        # Search by name, get info
        if cmd in aliases:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_charinfo(self, filter, channel, author)
            return

        aliases = ['gettraits', 'gtr', 'sex']
        # Search by name, get traits
        if cmd in aliases:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_traits(self, filter, channel, author)
            return


        '''
        Trait commands
        '''

        aliases = ['traitdefine', 'trd']
        # Search by trait, get definition
        if cmd in aliases:
            await vndb.trait_define(self, args, channel)
            return

        aliases = ['traitsearch', 'trs']
        # Search by trait, get character
        if cmd in aliases:
            await vndb.trait_search(self, args, channel, author)
            return

        await channel.send('Invalid command. Try `.vn help`')
        return
