import discord, vndb

class vndbot(discord.Client):
    async def on_ready(self):
        print('connected')


    async def on_connect(self):
        vndb.login(self)
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

        if 'eroge' in message.content.lower():
            await vndb.interject(message)

        if not message.content.startswith('.vn '):
            return

        _, cmd, *args = message.content.lower().split(' ', 2)
        args = args[0] if args else None
        channel = message.channel

        aliases = ['search', 's', 'find', 'f']
        if cmd in aliases:
            filter = '(title ~ "{}")'.format(args)
            await vndb.search(self, filter, channel)
            return

        aliases = ['random', 'rand', 'r']
        if cmd in aliases:
            await vndb.random_search(self, channel)
            return

        aliases = ['tagsearch', 'tags', 'tag', 'ts', 't']
        if cmd in aliases:
            await vndb.tag_search(self, args, channel)
            return

        aliases = ['relations', 'related', 'rel']
        if cmd in aliases:
            filter = '(title ~ "{}")'.format(args)
            await vndb.relations(self, filter, channel)
            return

        aliases = ['character', 'char', 'c']
        if cmd in aliases:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.character(self, filter, channel)
            return

        aliases = ['characterinfo', 'charinfo', 'ci', 'characterstats', 'charstats', 'cs']
        if cmd in aliases:
            filter = '(name ~ "{}" or original ~ "{}")'.format(args, args)
            await vndb.characterinfo(self, filter, channel)
            return

        aliases = ['traitsearch', 'traits', 'trait', 'trs', 'tr']
        if cmd in aliases:
            await vndb.trait_search(self, args, channel)
            return

        aliases = ['help', 'h']
        if cmd in aliases:
            await vndb.help(self, channel)
            return
