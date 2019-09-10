import discord, glob, os, random

client = discord.Client()

@client.event
async def on_ready():
    choice = random.choice(glob.glob('avatars/*'))
    username = os.path.basename(choice).split('.', 1)[0]
    with open(choice, 'rb') as file:
        avatar = file.read()
    try:
        await client.user.edit(username=username, avatar=avatar)
    except:
        pass

with open('tokens/discord', 'r') as token:
    client.run(token.read().strip())
