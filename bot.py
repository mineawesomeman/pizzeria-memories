import os
import discord
from discord.ext import tasks
import message_reader_fs as mr
import datetime as dt
from dotenv import load_dotenv

## if you are getting an SSL error, check this thread https://github.com/Rapptz/discord.py/issues/4159#issuecomment-700615568

def makeFooter(message: mr.Message) -> str:
    if message.isDM():
        return "Messaged in " + message.channel.channel_name
    
    return "Messaged in #" + message.channel.channel_name + " in " + message.channel.server_name

def makeEmbed(message: mr.Message) -> discord.Embed:
    author_name = message.sender.nickname + " (" + message.sender.username + ")"
    url = message.getMessageLink()
    author_icon_url = message.sender.avatar

    title = "On this day " + str(dt.date.today().year - message.ts.year) + " years ago, *" + message.sender.nickname + "* said"
    description = message.content
    color = message.sender.color

    footer = makeFooter(message=message)
    footer_icon_url = message.channel.icon
    timestamp = message.ts

    msg = discord.Embed(color=discord.Color.from_str(color), title=title, description=description, timestamp=timestamp, url=url)
    msg.set_author(name=author_name, icon_url=author_icon_url)
    msg.set_footer(text=footer, icon_url=footer_icon_url)
    
    if len(message.attachments) > 0:
        attachment_url = message.attachments[0].url
        msg.set_image(url=attachment_url)

    return msg

async def sendMemory(channel, text = "") -> None: 
    msg = mr.getMessageFromToday()
    await channel.send(text, embed=makeEmbed(msg))

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

pizzeria = None
memoryChannel = None

@client.event
async def on_ready():
    global pizzeria
    global memoryChannel

    pizzeria = client.guilds[0]

    for channel in pizzeria.channels:
        if "memories" in channel.name:
            memoryChannel = channel

    assert memoryChannel != None

    background_task.start()

    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel != memoryChannel:
        username = message.author.global_name
        discord_sender_id = str(message.author.id)
        nickname = message.author.display_name
        color = str(message.author.color)
        avatar = str(message.author.display_avatar)
        sender = mr.Person(username, discord_sender_id, nickname, color, avatar)

        server_name = message.channel.guild.name
        channel_name = message.channel.name
        icon = str(message.channel.guild.icon)
        channel_id = str(message.channel.id)
        server_id = str(message.channel.guild.id)
        channel = mr.Channel(server_name, channel_name, icon, channel_id, server_id)

        content = message.content
        ts = message.created_at
        discord_message_id = str(message.id)
        attachments = list()

        for attachment in message.attachments:
            attachment_name = attachment.filename
            attachment_url = attachment.url

            attachments.append(mr.Attachment(attachment_url, attachment_name))

        message = mr.Message(sender, channel, content, ts, discord_message_id, attachments)

        mr.putMessage(message)
    else:
        if message.content.startswith('$bot-check'):
            await message.channel.send('The bot is alive!!!')
        
        if message.content.startswith('$memory'):
            await sendMemory(memoryChannel)

        if message.content.startswith("$date"):
            await message.channel.send(f"Today's date is {dt.date.today()}")

        if message.content.startswith("$message"):
            words = message.content.split()
            if len(words) >= 2:
                key = words[1]
                to_send = mr.getMessage(key)
                if to_send is not None:
                    embed = makeEmbed(to_send)
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(f"Unable to find message with id {key}")
            else:
                await message.channel.send("Usage: $message <key>")

@tasks.loop(minutes=1)
async def background_task():
    global memoryChannel

    now = dt.datetime.now()
    if now.minute == 0 and now.hour == 9:
        await sendMemory(memoryChannel, "Message of the day @everyone")
    
    if now.minute == 0 and now.hour == 2:
        mr.updateTodaysMessages()

client.run(TOKEN)