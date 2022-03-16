import discord, datetime, re, os
from discord.ext import commands, tasks
from mctools import RCONClient

RCON_HOST = str(os.environ.get("rcon_host"))
RCON_PORT = int(os.environ.get("rcon_port"))
RCON_PASS = str(os.environ.get("rcon_pass"))
MANAGER_ROLE = int(os.environ.get("whitelist_manager"))

prefixes = ["-"]
bot = commands.Bot(command_prefix=prefixes)

# Extensions
bot.load_extension("jishaku")

# Default Commands
bot.remove_command("help")

prefix      = prefixes[0]
embed_color = 0x7289DA

def run_rcon(cmd):
    rcon = RCONClient(RCON_HOST, port=RCON_PORT)
    rcon_up = rcon.login(RCON_PASS)
    if rcon.is_authenticated() and rcon_up:
        res = rcon.command(cmd)
        rcon.stop()
        ansi_escape = re.compile(r'''
            \x1B  # ESC
            (?:   # 7-bit C1 Fe (except CSI)
                [@-Z\\-_]
            |     # or [ for CSI, followed by a control sequence
                \[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
        ''', re.VERBOSE)
        res = ansi_escape.sub('', res)
        return str(res)
    else:
        return "Failed to connect to server"

# Events
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    embed=discord.Embed(
        title       = ":x: An internal error occurred",
        description = f"`{str(error).replace('Command raised an exception: ', '')}`",
        color       = 0xFF0000
    )
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text = str(bot.user.name).lower())
    await ctx.send(embed = embed)

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or message.author.bot:
        return

    if message.content == f"<@!{bot.user.id}>" or message.content == f"<@!{bot.user.id}> prefix":
        await message.channel.send(f"{message.author.mention}, my prefix is: `{prefix}`")

    await bot.process_commands(message)

# Commands
@bot.command()
async def help(ctx):
    message_channel = ctx.channel
    embed = discord.Embed(
        title       = f"Bot Commands",
        colour      = embed_color,
        description = f"`{prefix}help` • help\
\n`{prefix}online` • check who's online"
    )
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="shitty bot made by senoe")
    await message_channel.send(embed=embed)

@bot.command(aliases=["rcon"])
async def exec(ctx, *, command):
    app_info = await bot.application_info()
    if ctx.author.id != app_info.owner.id:
        await ctx.send(":x: Only the bot owner can execute this command.")
    else:
        await ctx.send(run_rcon(command))

@bot.command()
@commands.guild_only()
async def whitelist(ctx, *args):
    if not discord.utils.get(ctx.guild.roles, id = MANAGER_ROLE) in ctx.author.roles:
        return await ctx.send(":x: You do not have permission to execute this command.")
    if not args:
        return await ctx.send(run_rcon("whitelist list"))
    else:
        args0 = str(args[0]).lower()
        if args0 == "list":
            return await ctx.send(run_rcon("whitelist list"))
        elif args0 == "add" or args0 == "remove":
            if not args[1]:
                return await ctx.send(f"Usage: {prefix}whitelist {args0} [player]")
            else:
                return await ctx.send(str(run_rcon(f"whitelist {args0} {args[1]}")).replace("Added ", ":white_check_mark: Added ").replace("Removed ", ":white_check_mark: Removed "))
        else:
            return await ctx.send(":x: Invalid command.")

@bot.command(aliases=["list"])
async def online(ctx):
    res = str(run_rcon("listplayers"))
    first_line = res.split("\n")[0]

    if res[1]:
        other_lines = res.replace(first_line, "")
    else:
        other_lines = None

    embed=discord.Embed(
        title       = first_line,
        description = other_lines,
        color       = embed_color
    )
    embed.timestamp = datetime.datetime.utcnow()
    await ctx.send(embed=embed)

# Tasks
@tasks.loop(seconds=120)
async def bot_status():
    member_count = 0
    for guild in bot.guilds:
        member_count += guild.member_count
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{member_count} members"))

@bot.event
async def on_ready():
    print(f"{bot.user} is ready for operation. beep boop!")
    bot_status.start()

bot.run(str(os.environ.get("token")))
