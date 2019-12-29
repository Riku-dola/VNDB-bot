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

        if 'eroge' in message.content.lower() and not message.content.startswith('.vn '):
            await vndb.interject(message)

        if not message.content.startswith('.vn '):
            return

        _, cmd, *args = message.content.lower().split(' ', 2)
        args = args[0] if args else None
        channel = message.channel
        author = message.author

        if cmd in ['help', 'h']:
            await vndb.help(self, channel)
            return


        '''
        Game commands
        '''

        # Search by name, find description
        if cmd in ['search', 's', 'find', 'f']:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.search(self, filter, channel, author=author)
            return

        # Search by name, find tags
        if cmd in ['gettags', 'gt']:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_tags(self, filter, channel, author)
            return

        # Search by name, find related novels
        if cmd in ['getcharacters', 'getchars', 'gc']:
            await vndb.get_characters(self, args, channel, author)
            return

        # Search by name, find related novels
        if cmd in ['getrelations', 'getrelated', 'gr']:
            filter = '(title ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_relations(self, filter, channel, author)
            return

        # Get random novel
        if cmd in ['random', 'rand', 'r']:
            await vndb.get_random(self, channel)
            return


        '''
        Tag commands
        '''

        # Search by tag, get definition
        if cmd in ['tagdefine', 'td']:
            await vndb.tag_define(self, args, channel)
            return

        # Search by tag, get novels
        if cmd in ['tagsearch', 'ts']:
            await vndb.tag_search(self, args, channel, author)
            return


        '''
        Character commands
        '''

        # Search by name, get description
        if cmd in ['character', 'char', 'c']:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.search_character(self, filter, channel, author)
            return

        # Search by name, get info
        if cmd in ['getcharinfo', 'charinfo', 'gci', 'gi']:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_charinfo(self, filter, channel, author)
            return

        # Search by name, get traits
        if cmd in ['gettraits', 'gtr', 'sex']:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.get_traits(self, filter, channel, author)
            return


        '''
        Trait commands
        '''

        # Search by trait, get definition
        if cmd in ['traitdefine', 'trd']:
            await vndb.trait_define(self, args, channel)
            return

        # Search by trait, get character
        if cmd in ['traitsearch', 'trs']:
            await vndb.trait_search(self, args, channel, author)
            return

        await channel.send('Invalid command. Try `.vn help`')
        return
