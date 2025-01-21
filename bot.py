import os
import discord
import message_reader as mr
import datetime as dt
from dotenv import load_dotenv

def makeFooter(message: mr.Message):
    if message.channel.server_id == 0:
        return "Messaged in " + message.channel.channel_name
    
    return "Messaged in #" + message.channel.channel_name + " in " + message.channel.server_name

def makeEmbed(message: mr.Message):
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

    return msg

async def sendMemory(channel):
    msg = mr.getMessageFromToday()
    await channel.send(embed=makeEmbed(msg))

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

    # await memoryChannel.send("golden freddie is alive")

    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel != memoryChannel:
        return

    if message.content.startswith('$bot-check'):
        await message.channel.send('The bot is alive!!!')
    
    if message.content.startswith('$memory'):
        await sendMemory(memoryChannel)
    
    if message.content.startswith("$date"):
        await message.channel.send(f"Today's date is {dt.date.today()}")

client.run(TOKEN)