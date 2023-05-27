from config import token
import discord

bot = discord.Client(intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot Information:")
    print("Username: {}".format(bot.user.name))
    print("Discriminator: {}".format(bot.user.discriminator))
    print("User ID: {}".format(bot.user.id))
    print("Server Count: {}".format(len(bot.guilds)))
    print("Member Count: {}".format(sum(len(guild.members) for guild in bot.guilds)))
    print("Bot is connected to the following servers:")
    for guild in bot.guilds:
        print("- {} (ID: {})".format(guild.name, guild.id))
        print("  Member Count: {}".format(len(guild.members)))
        # print("  Channels:")
        # for channel in guild.channels:
        #     print("  - {} (ID: {})".format(channel.name, channel.id))
        print("---------------")

    # Shard Information
    print("Shard Information:")
    print("Shard ID: {}".format(bot.shard_id))
    print("Total Shards: {}".format(bot.shard_count))
    print("---------------")

    await bot.close()
    # raise SystemExit

bot.run(token)