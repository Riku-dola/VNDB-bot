import discord, glob, os, random

client = discord.Client()

@client.event
async def on_ready():
    choice = random.choice(glob.glob('avatars/*'))
    nick = os.path.basename(choice).split('.', 1)[0]
    with open(choice, 'rb') as file:
        avatar = file.read()
    try:
        await client.user.edit(nick=nick, avatar=avatar)
    except:
        pass
    await client.logout()

with open('tokens/discord', 'r') as token:
    client.run(token.read().strip())
