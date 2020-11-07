import asyncio
from vndbot import *

bot = vndbot(intents=discord.Intents.all())

try:
    main_loop = asyncio.get_event_loop()
    with open('tokens/discord', 'r') as token:
        main_loop.run_until_complete(bot.start(token.read().strip()))

except KeyboardInterrupt:
    main_loop.run_until_complete(bot.logout())

finally:
    main_loop.close()
