import discord
from discord import Embed
from discord import app_commands
from discord.ext import commands
from discord import ui
from discord import Interaction
from discord.ext.commands import MissingRequiredArgument
from discord.errors import HTTPException, Forbidden
import json
from databaseutil import *
import traceback
import requests
import os
import datetime
import itertools
import asyncio

# CONFIG
from config import *

bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())

success_emoji = discord.PartialEmoji(name="passed", id=1096972201296674857)
error_emoji = discord.PartialEmoji(name="failed", id=1096972119033786479)

if not os.path.exists("data.json"):
    with open("data.json", "w") as file:
        json.dump({}, file)

def success_embed(description):
    embed = discord.Embed(title="Operation completed successfully", description=f"{str(success_emoji)} - {description}")
    embed.set_footer(text=f"{application_name} - Developed by {bot_developer}")
    return embed

def error_embed(description):
    embed = discord.Embed(title="Operation failed", description=f"{str(error_emoji)} - {description}")
    embed.set_footer(text=f"{application_name} - Developed by {bot_developer}")
    return embed

@bot.event
async def on_guild_join(guild):
    server_id = str(guild.id)
    # Create entry with default values
    create_or_update_entry(server_id)

@bot.event
async def on_guild_remove(guild):
    server_id = str(guild.id)
    # Delete entry
    delete_entry(server_id)

def find_empty_values(json_data):
    if json_data is None:
        return None

    empty_values = []
    for key, value in json_data.items():
        if key != "logging_webhook" and value == "":
            empty_values.append(key)
            
    if len(empty_values) == 0:
        return None
    else:
        return empty_values

status_cycle = itertools.cycle(statuses)

@bot.event
async def on_ready():
    print("Bot Information:")
    print("Username: {}".format(bot.user.name))
    print("Discriminator: {}".format(bot.user.discriminator))
    print("User ID: {}".format(bot.user.id))
    print("Server Count: {}".format(len(bot.guilds)))
    print("Member Count: {}".format(sum(len(guild.members) for guild in bot.guilds)))

    # for shard_id in bot.shard_ids:
    #     print("Shard ID: {}".format(shard_id))
    #     print("Shard Count: {}".format(bot.shard_count))

    print("Bot is ready!")

    # Start the status rotation task
    bot.loop.create_task(rotate_status())

async def rotate_status():
    while True:
        new_status = next(status_cycle)

        if status_type.lower() == "streaming":
            activity = discord.Streaming(name=new_status, url=streaming_url)
        else:
            activity = discord.Game(name=new_status)

        await bot.change_presence(activity=activity)
        await asyncio.sleep(60)  # Change the interval as desired


async def log_action(server_id, action, user=None, description=None):
    webhook_url = get_logging_webhook_value(str(server_id))
    if webhook_url is None:
        return None
    if user is None:
        username = "N/A"
        user_id = "N/A"
    else:
        username = f"{user.username}#{user.discrim}"
        user_id = user.id
    embed = discord.Embed()
    embed.title = f"Verification Bot Logs - {action}"
    if description is not None:
        timestamp = datetime.now().timestamp()
        formatted_timestamp = int(timestamp)
        embed.description = f"{description}\n\nAction executed at: <t:{formatted_timestamp}:F>\nAction executed by {username} ({user_id})"
    
    webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter())
    await webhook.send(embed=embed, username=f"{application_name} - Logging")
    return True


@commands.is_owner()
@bot.command(name="sync", description="Sync all slash commands.")
async def sync(ctx):
    try:
        msg = await ctx.send("Syncing...")
        print("Syncing...")
        synced = await bot.tree.sync()
        await msg.edit(content=f"Synced! {len(synced)} commands synced.")
        print(f"Synced! {len(synced)} commands synced.")
    except Exception as e:
        await ctx.send(content=f"Error: {e}")
        print(f"Error: {e}")

@bot.tree.command(name="init", description="Create JSON data for a guild")
async def initcmd(interaction: discord.Interaction):
    if interaction.user.id != int(owner_id):
        embed = error_embed("Sorry, you do not have permission to use this command.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    server_id = str(interaction.guild.id)
    existing_data = get_data_for_server(server_id)

    if existing_data is not None:
        # Confirmation message
        confirmation_message = (
            "⚠️ JSON data already exists for this guild. Running this command will overwrite the existing data. "
            "This action cannot be undone. Are you sure you want to proceed?\n\n"
            "To proceed, type:\n"
            "`confirm overwrite`"
        )

        # Ask for confirmation
        confirmation_embed = discord.Embed(
            title="Confirmation",
            description=confirmation_message,
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=confirmation_embed)

        def check_confirmation(message):
            return (
                message.author == interaction.user
                and message.channel == interaction.channel
                and message.content.strip().lower() == "confirm overwrite"
            )

        try:
            # Wait for user confirmation
            confirmation_response = await bot.wait_for("message", check=check_confirmation, timeout=60.0)
        except TimeoutError:
            # Confirmation timeout
            timeout_embed = discord.Embed(
                title="Confirmation Timeout",
                description="The overwrite confirmation has timed out. Please run the command again if you wish to proceed.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=timeout_embed)
            return

        # Overwrite existing data
        create_or_update_entry(server_id)

        await interaction.followup.send(embed=success_embed("JSON data overwritten for this guild."))
    else:
        # Create a new entry with default values
        create_or_update_entry(server_id)

        await interaction.followup.send(embed=success_embed("JSON data created for this guild."))


@bot.tree.command(name="verify")
@app_commands.describe(member="The member to force verify (Staff Only)")
async def verify(interaction: Interaction, member: discord.Member = None):
    server_id = interaction.guild.id

    x = find_empty_values(get_data_for_server(str(server_id)))
    if x is not None:
        # Check if the user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            embed = error_embed("Some config values were not provided. Please contact a server admin to fix this.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = error_embed("Some config values were not provided.")
            if 'staff_role_id' in x:
                command_staff = f"</config_staffrole:1108376766059384992>"
                embed.add_field(name="Staff Role", value=f"You may set it by using the command: {command_staff}", inline=False)
            if 'verified_role_id' in x:
                command_verified = f"</config_verifiedrole:1108369164361535560>"
                embed.add_field(name="Verified Role", value=f"You may set it by using the command: {command_verified}", inline=False)

            if 'staff_role_id' in x and 'verified_role_id' in x:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif 'staff_role_id' in x:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif 'verified_role_id' in x:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    config = get_data_for_server(str(interaction.guild.id))
    staff_role_id = int(config["staff_role_id"])
    verified_role_id = int(config["verified_role_id"])
    verified_role = interaction.guild.get_role(int(verified_role_id))
    staff_role = interaction.guild.get_role(int(staff_role_id))
    if staff_role not in interaction.user.roles and member is not None:
        member = None
        user_id = str(interaction.user.id)
    
    if member is not None:
        user_id = str(member.id)
    else:
        user_id = str(interaction.user.id)
    user = interaction.guild.get_member(int(user_id))
    staffgrant = True if user_id != str(interaction.user.id) else False

    url = f'{base_url}/discord/check_status?discord_id=' + user_id  # Replace with the actual URL
    headers = {'Authorization': auth_token}

    response = requests.get(url, headers=headers)
    try:
        data = response.json()
        print(data)
        rtoken = data["token"]
        rserver_id = data["server_id"]
        renabled = data["enabled"]
    except:
        rtoken = None
        renabled = None
        pass

    if verified_role in user.roles:
        embed = error_embed(f"The user {user.mention} is already verified. Contact a server staff member if this is an error.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if response.status_code != 200 or renabled == 1 and staffgrant is False:
        if response.status_code == 404 or renabled == 1:
            # Prepare headers with authentication, Discord ID, and Server ID
            headers = {
                'Authorization': auth_token,
                'Discord-Id': str(user_id),
                'Server-Id': str(server_id)
            }

            # Make a GET request to the create_token endpoint
            if rtoken is None:
                response = requests.get(f'{base_url}/discord/create_token', headers=headers)
            else:
                response = requests.get(url, headers=headers)
            print(response.json())

            # Check the response status code
            if response.status_code == 200:
                # Token creation successful
                data = response.json()
                token = data['token']
                embed = success_embed(f"Successfully generated link.\nPlease verify at: {base_url}/discord/verify?token={token}")
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = error_embed("There was a problem creating your token. Please contact a developer.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = error_embed(f"Web server did not return code 200. Here is some info:\n```json\n{response}\n```")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    delete_url = f"{base_url}/discord/delete_token"
    requests.post(url=delete_url, headers={'Authorization': auth_token, "token": rtoken})

    if rserver_id != server_id:
        embed = error_embed("Server ID does not match. This usually occurs when you haven't finished verifying in a different server. It can usually be fixed by rerunning the command. If the problem persists, contact a developer.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if verified_role_id:
        if verified_role:
            if user:
                if staffgrant:
                    await user.add_roles(verified_role, reason="Verified role granted by staff")
                    embed = success_embed(f"Verified role has been applied to the user: {user.mention} ({user.id})")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    # Log the action with staff user
                    await log_action(server_id, "verify", user=interaction.user, description="User verification executed by staff")
                else:
                    await user.add_roles(verified_role, reason="Verified role applied by member")
                    embed = success_embed(f"You have been successfully verified.")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    # Log the action with member user
                    await log_action(server_id, "verify", user=user, description="User verification executed by member")
            else:
                embed = error_embed("The user could not be found. Please make sure the ID is correct.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = error_embed("The verified role does not exist. Please contact a server admin.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    else:
        embed = error_embed("The verified role ID is not configured. Please contact a server admin.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

@bot.tree.command(name="config_verifiedrole")
@app_commands.commands.describe(role="The verified role to give.")
async def config_verifiedrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        embed = error_embed("You do not have permission to run this command.")
        await interaction.response.send_message(embed=embed)
        return

    set_verified_role_id(str(interaction.guild.id), str(role.id))

    embed = success_embed(f"Successfully linked the role: {role.mention}.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="config_staffrole")
@app_commands.commands.describe(role="The staff role (Will have access to most features)")
async def config_staffrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        embed = error_embed("You do not have permission to run this command.")
        await interaction.response.send_message(embed=embed)
        return

    set_staff_role_id(str(interaction.guild.id), str(role.id))

    embed = success_embed(f"Successfully linked the role: {role.mention}.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="config_logswebhook")
@app_commands.commands.describe(webhook="The webhook that will be used for logging purposes.")
async def config_logswebhook(interaction: discord.Interaction, webhook: str):
    if not interaction.user.guild_permissions.administrator:
        embed = error_embed("You do not have permission to run this command.")
        await interaction.response.send_message(embed=embed)
        return

    set_logging_webhook(str(interaction.guild.id), str(webhook))

    embed = success_embed(f"Successfully set the logging webhook to:\n{webhook}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="invite", description="Get an invite link for the bot!")
async def invite_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Bot Invite", description="You can invite the bot using this link:\n\nhttps://discord.com/oauth2/authorize?client_id=1100503947992637561&permissions=8&redirect_uri=https%3A%2F%2Fapi.jinxz.dev%2Fdiscord%2Fthanks&response_type=code&scope=identify%20bot%20applications.commands")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    return

@bot.command(name="howto", aliases=["ht", "tutorial", "instructions"])
async def howto(ctx):
    embed = discord.Embed(
        title="How to verify",
        description="To gain access to this discord server you must verify that you are not a robot.\n\nTo verify follow these steps:\n**1.** Run the command </verify:1107825122947104828>\n**2.** Click on the link that is provided\n**3.** Click Verify (on the website)\n**4.** Run the command </verify:1107825122947104828> again.\n**5.** You are now verified!",
    )
    embed.set_footer(text="Auth Bot - Made by jinxz#1337")

    await ctx.send(embed=embed)
    await ctx.message.delete()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        if error.param.name == "channel":
            embed = error_embed("Channel is a required argument. Example: `PREFIXsetup #channel`")
            await ctx.send(embed=embed)
    elif isinstance(error, (HTTPException, Forbidden)):
        # Rate limiting handling
        embed = error_embed("Command failed due to rate limiting. Please try again later.")
        await ctx.send(embed=embed)
    else:
        # Other errors
        error_message = f"An error occurred while executing the command: {error}"
        print(f"Command Error: {error_message}")
        traceback.print_exc()  # Print detailed traceback to console

        embed = error_embed(error_message)
        await ctx.send(embed=embed)
        raise error

@bot.command()
async def setup(ctx):
    if not ctx.author.guild_permissions.administrator:
        embed = error_embed("You do not have permission to run this command.")
        await ctx.reply(embed=embed)
        return
    x = find_empty_values(get_data_for_server(str(ctx.guild.id)))
    if x is not None:
        embed = error_embed("Some config values were not provided.")
        if 'staff_role_id' in x:
            command_staff = f"</config_staffrole:1108376766059384992>"
            embed.add_field(name="Staff Role", value=f"You may set it by using the command: {command_staff}", inline=False)
        if 'verified_role_id' in x:
            command_verified = f"</config_verifiedrole:1108369164361535560>"
            embed.add_field(name="Verified Role", value=f"You may set it by using the command: {command_verified}", inline=False)

        if 'staff_role_id' in x and 'verified_role_id' in x:
            await ctx.reply(embed=embed)
        elif 'staff_role_id' in x:
            await ctx.reply(embed=embed)
        elif 'verified_role_id' in x:
            await ctx.reply(embed=embed)
        return



    
    config = get_data_for_server(str(ctx.guild.id))
    verified_role_id = int(config["verified_role_id"])
    verified_role = ctx.guild.get_role(verified_role_id)
    staff_channels = ["staff", "logs", "log", "admin", "moderator", "admin-logs"]

    # Confirmation message
    confirmation_message = (
        "⚠️ Running this command will modify channel permissions for setup. "
        "This action cannot be undone. Are you sure you want to proceed?\n\n"
        "To proceed, type:\n"
        "`confirm setup`"
    )

    # Ask for confirmation
    confirmation_embed = discord.Embed(
        title="Confirmation",
        description=confirmation_message,
        color=discord.Color.gold()
    )
    confirmation_prompt = await ctx.reply(embed=confirmation_embed)

    def check_confirmation(message):
        return (
            message.author == ctx.author
            and message.channel == ctx.channel
            and message.content.strip().lower() == "confirm setup"
        )

    try:
        # Wait for user confirmation
        confirmation_response = await bot.wait_for("message", check=check_confirmation, timeout=60.0)
    except TimeoutError:
        # Confirmation timeout
        timeout_embed = discord.Embed(
            title="Confirmation Timeout",
            description="The setup confirmation has timed out. Please run the command again if you wish to proceed.",
            color=discord.Color.red()
        )
        await confirmation_prompt.edit(embed=timeout_embed)
        return

    # Remove the confirmation prompt
    await confirmation_prompt.delete()

    channel = ctx.message.channel_mentions[0]

    updated_channels = []

    # Remove permissions from all channels
    for guild_channel in ctx.guild.channels:
        if isinstance(guild_channel, discord.TextChannel):
            overwrites = guild_channel.overwrites_for(ctx.guild.default_role)
            if guild_channel == channel:
                # Add permissions for specified channel
                overwrites.update(view_channel=True, send_messages=True)
            else:
                # Remove permissions from other channels
                overwrites.update(view_channel=False, send_messages=False)

            channel_name = guild_channel.name.lower()
            category_name = guild_channel.category.name.lower() if guild_channel.category else ""
            is_staff_channel = any(keyword in channel_name or keyword in category_name for keyword in staff_channels)

            if is_staff_channel:
                # Exclude staff channels from modifications
                overwrites.update(view_channel=True, send_messages=True)

            await guild_channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
            updated_channels.append(guild_channel.mention)

    # Add permissions for verified role in public channels
    for guild_channel in ctx.guild.channels:
        if isinstance(guild_channel, discord.TextChannel) and not guild_channel.permissions_for(verified_role).view_channel:
            channel_name = guild_channel.name.lower()
            category_name = guild_channel.category.name.lower() if guild_channel.category else ""
            is_staff_channel = any(keyword in channel_name or keyword in category_name for keyword in staff_channels)

            if not is_staff_channel:
                # Exclude staff channels from modifications
                await guild_channel.set_permissions(verified_role, read_messages=True, send_messages=True)
                updated_channels.append(guild_channel.mention)

    # Construct the reply message
    if updated_channels:
        channel_mentions = "\n".join(updated_channels)
        reply_message = f"Setup completed. Updated channels:\n{channel_mentions}"
    else:
        reply_message = "Setup completed. No channels were updated."

    reply_message += "\n\nYou can use `?howto` to send an embed."

    await ctx.send(reply_message)
bot.run(token)