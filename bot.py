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
import aiohttp
import re

# CONFIG
from config import *

bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())

success_emoji = discord.PartialEmoji(name="passed", id=1096972201296674857)
error_emoji = discord.PartialEmoji(name="failed", id=1096972119033786479)

if not os.path.exists("data.json"):
    with open("data.json", "w") as file:
        json.dump({}, file)

def success_embed(description: str) -> discord.Embed:
    """
    Create an embedded message indicating a successful operation.

    Parameters:
    - description (str): The description of the success message.

    Returns:
    - discord.Embed: The embedded message indicating success.
    """
    embed = discord.Embed(title="Operation completed successfully", description=f"{str(success_emoji)} - {description}")
    embed.set_footer(text=f"{application_name} - Developed by {bot_developer}")
    return embed

def error_embed(description: str) -> discord.Embed:
    """
    Create an embedded message indicating an error or failed operation.

    Parameters:
    - description (str): The description of the error message.

    Returns:
    - discord.Embed: The embedded message indicating an error.
    """
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

    for guild in bot.guilds:
        server_id = str(guild.id)
        server_data = get_data_for_server(server_id)

        if not server_data:
            create_or_update_entry(server_id, premium=False, status=True)
            print(f"Created server data for guild '{guild.name}' with ID '{server_id}'")

    # for shard_id in bot.shard_ids:
    #     print("Shard ID: {}".format(shard_id))
    #     print("Shard Count: {}".format(bot.shard_count))

    print("Bot is ready!")

    # Start the status rotation task
    bot.loop.create_task(rotate_status())

async def rotate_status():
    while True:
        new_status = next(status_cycle)
        status_parts = new_status.split(":::")

        # Fetch server count
        server_count = len(bot.guilds)

        # Fetch member count from all guilds the bot is in
        member_count = sum(len(guild.members) for guild in bot.guilds)

        # Replace custom variables in the status text
        new_status = status_parts[0].replace('${server_count}', str(server_count))
        new_status = new_status.replace('${member_count}', str(member_count))

        # Determine the status type
        if len(status_parts) > 1:
            status_type = status_parts[1]
        else:
            status_type = status_type.lower()

        # Set the appropriate activity based on the status type
        if status_type == "streaming":
            activity = discord.Streaming(name=new_status, url=streaming_url)
        else:
            activity = discord.Activity(type=getattr(discord.ActivityType, status_type), name=new_status)

        await bot.change_presence(activity=activity)
        await asyncio.sleep(30)  # Change the interval as desired

async def guild_updater():
    if not statsupdater_enabled:
        return
    
    if botsgg_token and botsgg_token != "":
        requests.post(f"https://discord.bots.gg/api/v1/bots/{bot.user.id}/stats", json={"guildCount": bot.guilds.count}, headers={"Content-Type": "application/json", "Authorization": statsupdater_enabled(botsgg_token)})

    if botsfordiscord_token and botsfordiscord_token != "":
        requests.post(f"https://discords.com/bots/api/bot/" + str(bot.user.id), json={"server_count": bot.guilds.count}, headers={"Authorization": str(botsfordiscord_token)})

    await asyncio.sleep(600)

async def log_action(server_id, action, user=None, description=None):
    webhook_url = get_logging_webhook_value(str(server_id))
    if webhook_url is None or webhook_url == "":
        return None

    if user is None:
        username = "N/A"
        user_id = "N/A"
    else:
        username = f"{user.name}#{user.discriminator}"
        user_id = user.id
    embed = discord.Embed()
    embed.title = f"Verification Bot Logs - {action}"
    if description is not None:
        timestamp = datetime.datetime.now().timestamp()
        formatted_timestamp = int(timestamp)
        embed.description = f"{description}\n\nAction executed at: <t:{formatted_timestamp}:F>\nAction executed by {username} ({user_id})"
    
    session = aiohttp.ClientSession()
    webhook = discord.Webhook.from_url(webhook_url, session=session)
    await webhook.send(embed=embed, username=f"{application_name} - Logging")
    await session.close()
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
    user_id = None
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

    try:
        status = config["status"]
    except KeyError:
        set_status(interaction.guild.id, True)
        embed = success_embed("Updated config. Please rerun the command.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if status is False:
        embed = error_embed("Sorry, the verification system is currently disabled in this server.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user = interaction.guild.get_member(int(user_id))
    staffgrant = True if int(user_id) != int(interaction.user.id) else False

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
        rserver_id = None
        pass

    if verified_role in user.roles:
        embed = error_embed(f"The user {user.mention} is already verified. Contact a server staff member if this is an error.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if response.status_code != 200 or renabled == 1:
        if staffgrant is False:
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
        else:
            pass
        # embed = error_embed(f"Web server did not return code 200. Here is some info:\n```json\n{response}\n```")
        # await interaction.response.send_message(embed=embed, ephemeral=True)
        # return
    
    try: requests.post(url=f"{base_url}/discord/delete_token", headers={'Authorization': auth_token, "token": rtoken})
    except: pass

    if rserver_id is not None:
        if rserver_id != server_id:
            embed = error_embed("Server ID does not match. This usually occurs when you haven't finished verifying in a different server. It can usually be fixed by rerunning the command. If the problem persists, contact a developer.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    if verified_role_id:
        if verified_role:
            if user:
                try:
                    if staffgrant:
                        await user.add_roles(verified_role, reason="Verified role granted by staff")
                        embed = success_embed(f"Verified role has been applied to the user: {user.mention} ({user.id})")
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        # Log the action with staff user
                        await log_action(server_id, "Successful Verification", user=interaction.user, description="User verification executed by staff")
                        increment_total_verifications(server_id)
                        return
                    else:
                        await user.add_roles(verified_role, reason="Verified role applied by member")
                        embed = success_embed(f"You have been successfully verified.")
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        # Log the action with member user
                        await log_action(server_id, "Successful Verification", user=user, description="User verification executed by member")
                        increment_total_verifications(server_id)
                        return
                except discord.errors.Forbidden:
                    embed = error_embed("Could not verify member. Please make sure I have sufficient permissions and my role is above the verified role.")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
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

@bot.tree.command(name="config_verifiedrole", description="Set a role to be given apon successful verification.")
@app_commands.commands.describe(role="The verified role to give.")
async def config_verifiedrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        embed = error_embed("You do not have permission to run this command.")
        await interaction.response.send_message(embed=embed, delete_after=10)
        return
    
    if role.name == "@everyone":
        embed = error_embed("Invalid role. Please specify a role other than @everyone.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    set_verified_role_id(str(interaction.guild.id), str(role.id))

    embed = success_embed(f"Successfully linked the role: {role.mention}.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="config_staffrole", description="Set a role to be used for staff.")
@app_commands.commands.describe(role="The staff role (Will have access to most features)")
async def config_staffrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        embed = error_embed("You do not have permission to run this command.")
        await interaction.response.send_message(embed=embed, delete_after=10)
        return

    if role.name == "@everyone":
        embed = error_embed("Invalid role. Please specify a role other than @everyone.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    set_staff_role_id(str(interaction.guild.id), str(role.id))

    embed = success_embed(f"Successfully linked the role: {role.mention}.")
    await interaction.response.send_message(embed=embed)

def is_valid_webhook(webhook: str) -> bool:
    # This is broken so for now it returns True 24/7

    # # Check if the URL starts with the correct prefix
    # if not webhook.startswith("https://discord.com/api/webhooks/"):
    #     return False

    # # Split the URL and retrieve the webhook ID and token
    # parts = webhook.split("/")
    # if len(parts) != 7:
    #     return False

    # # Check if the webhook ID and token are alphanumeric
    # webhook_id = parts[-2]
    # webhook_token = parts[-1]
    # if not webhook_id.isalnum() or not webhook_token.isalnum():
    #     return False

    return True

@bot.tree.command(name="config_logswebhook", description="Set a channel to be used for logging")
@app_commands.commands.describe(channel="The channel where the webhook will be created for logging purposes.")
async def config_logswebhook(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(embed=error_embed("You do not have permission to run this command."), delete_after=10)
        return

    webhook = await channel.create_webhook(name=f"{application_name} - Logging", avatar="https://beta.jinxz.dev/u/pSv5U9.jpg")
    set_logging_webhook(str(interaction.guild.id), webhook.url)

    await interaction.response.send_message(embed=success_embed(f"Successfully created and set the logging webhook in channel {channel.mention}"), ephemeral=True)
    return

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
            embed = error_embed("Channel is a required argument. Example: `?command #channel`")
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
        await ctx.reply(embed=embed)
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


@bot.tree.command(name="status", description="Enable / Disable the verification system.")
@app_commands.describe(status = "True = Enable, False = Disable")
async def status(interaction: discord.Interaction, status: bool):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(embed=error_embed("You do not have permission to run this command."), delete_after=10)
        return
    set_status(interaction.guild.id, status)
    text = "enabled" if status else "disabled"
    embed = success_embed(f"Successfully {text} the verification system.")
    await interaction.response.send_message(embed=embed)
    return

@bot.tree.command(name="help", description="Display a list of commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed()
    embed.description = """Slash Commands:
</verify:1107825122947104828> - Get verified
</invite:1108449958429982720> - Get a bot invite link
</config_verifiedrole:1108369164361535560> - Set the server's verified role
</config_staffrole:1108376766059384992> - Set the server's staff role
</config_logswebhook:1108834646231351418> - Set a channel to use for logging
</status:1108932074687172689> - Change the status of the verification system. (Enable/Disable it)

Other Commands:
?howto - Display an embed telling users how to verify
?setup #channel - Set permissions (This command is risky and may expose private channels. Use at own risk)"""

    await interaction.response.send_message(embed=embed, ephemeral=True)
    return

bot.run(token)