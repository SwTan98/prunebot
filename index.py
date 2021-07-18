import asyncio
import discord
import math
import os
from datetime import datetime, timedelta
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("TOKEN")

description = """Bot to search for specific role members and remove role if inactive"""
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="~", description=description, intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.command()
async def prune(ctx):
    guild = ctx.guild
    roles = guild.roles
    role_valid = False

    def check_user(user):
        return user.author == ctx.message.author

    def check_reaction(reaction, user):
        return user == ctx.message.author

    # Get role name
    async with ctx.channel.typing():
        await ctx.reply("Please enter a role name:")
    while not role_valid:
        msg = await bot.wait_for("message", check=check_user)
        role_name = msg.content
        for _role in roles:
            if _role.name.lower() == role_name.lower():
                role = _role
                role_valid = True
                break
        else:
            await msg.reply("Please enter a valid role")

    # Get inactivity days
    async with ctx.channel.typing():
        await ctx.reply(
            "Please enter a number for minimum inactivity in day(s) (eg: 365):"
        )
    while True:
        msg = await bot.wait_for("message", check=check_user)
        try:
            time_delta = int(msg.content)
            if time_delta < 0:
                raise ValueError("Positive integers only")
            break
        except ValueError:
            await msg.reply("Please enter a valid number")

    # Get reason
    try:
        async with ctx.channel.typing():
            await ctx.reply("Please enter a reason:")
        msg = await bot.wait_for("message", timeout=30, check=check_user)
        reason = msg.content
    except asyncio.TimeoutError:
        reason = ""
        await ctx.reply("No reason specified, continuing execution...")

    await ctx.reply("Searching for inactive users, this might take a while...")

    async with ctx.channel.typing():
        active_users = set()
        removed_users = []
        message_list = []
        role_users = [member for member in role.members]
        now = datetime.today()
        after = now - timedelta(days=time_delta)
        for channel in guild.text_channels:
            # temp hardcoded category ids
            if channel.category.id in [
                602662881045250096,
                568632818247270410,
                741840989219717213,
            ]:
                continue
            print("Scraping {}".format(channel.name))
            async for msg in channel.history(limit=None, after=after):
                active_users.add(msg.author)
            print("Active user count: {}".format(len(active_users)))
        inactive_users = [user for user in role_users if user not in active_users]

        if not len(inactive_users):
            await ctx.send(
                "No inactive members found for role {} within {} day(s)".format(
                    role.mention, time_delta
                )
            )
            return

        try:
            async with ctx.channel.typing():
                await ctx.send(
                    "__Role will be removed for {} members:__".format(
                        len(inactive_users)
                    )
                )
                for i in range(math.ceil(len(inactive_users) / 60)):
                    await ctx.send(
                        ", ".join(
                            [
                                user.mention
                                for user in inactive_users[i * 60 : i * 60 + 60]
                            ]
                        )
                    )
                msg = await ctx.reply("Would you like to proceed with the action?")
                await msg.add_reaction("❌")
                await msg.add_reaction("✅")
            reaction, user = await bot.wait_for(
                "reaction_add", timeout=60, check=check_reaction
            )
            if str(reaction.emoji) != "✅":
                await ctx.reply("Action cancelled")
                return
            for user in inactive_users:
                try:
                    await user.remove_roles(role, reason=reason)
                    removed_users.append(user)
                except discord.Forbidden:
                    await ctx.reply(
                        "No permission to remove role {} from user {}".format(
                            role.mention, user.mention
                        )
                    )
            if len(removed_users):
                await ctx.send(
                    "__Role removed for {} members:__".format(len(removed_users))
                )
                for i in range(math.ceil(len(removed_users) / 60)):
                    await ctx.send(
                        ", ".join(
                            [
                                user.mention
                                for user in removed_users[i * 60 : i * 60 + 60]
                            ]
                        )
                    )
            else:
                await ctx.send("Role is not removed from any members")

        except asyncio.TimeoutError:
            await ctx.reply("Reaction timeout, action cancelled")


bot.run(token)
