import json

from os import getcwd
from os import listdir
from os.path import isfile, join

from datetime import *
import numpy as np

class Channel:
    server_name: str = ""
    channel_name: str = ""
    icon: str = ""
    channel_id: str = ""
    server_id: str = ""

    def __init__(self, server_name: str, channel_name: str, icon: str, channel_id: int, server_id: int):
        self.server_name = server_name
        self.channel_name = channel_name
        self.icon = icon
        self.channel_id = channel_id
        self.server_id = server_id

class Person:
    username: str = ""
    discord_id: str = ""
    nickname: str = ""
    color: str = ""
    avatar: str = ""

    def __init__(self, username: str, discord_id: str, nickname: str, color: str, avatar: str):
        self.username = username
        self.discord_id = discord_id
        self.nickname = nickname
        self.color = color
        self.avatar = avatar
    
    def __hash__(self):
        return self.discord_id.__hash__()
    
    def __eq__(self, value):
        return self.discord_id == value.discord_id

class Attachment:
    url: str = ""
    name: str = ""

    def __init__(self, url: str, name: str):
        self.url = url
        self.name = name

class Message:
    sender: Person = None
    channel: Channel = None
    content: str = ""
    ts: datetime = datetime.min
    discord_id: str = ""
    attachments: list[Attachment] = []

    def __init__(self, sender: Person, channel: Channel, content: str, ts: datetime, discord_id: str, attachments: list):
        self.sender = sender
        self.channel = channel
        self.content = content
        self.ts = ts
        self.discord_id = discord_id
        self.attachments = attachments
    
    def __hash__(self) -> int:
        return self.discord_id.__hash__()
    
    def __eq__(self, value) -> bool:
        return self.discord_id == value.discord_id
    
    def isDM(self) -> bool:
        return self.channel.server_id == "0"

    def getMessageLink(self) -> str:
        if self.isDM():
            return "https://discord.com/channels/@me/" + self.channel.channel_id + "/" + self.discord_id
        return "https://discord.com/channels/" + self.channel.server_id + "/" + self.channel.channel_id + "/" + self.discord_id

channels = dict[str, Channel]()
people = dict[str, Person]()
messages = dict[str, Message]()
day_to_message = dict[date, list[Message]]()

def calcWeight(msg: Message) -> float:
    weight = 50

    words = msg.content.split()
    word_count = len(words)
    
    for word in words:
        # if a message has a content warning or other words that signal something bad, we don't want to considered 
        if word.lower() in ["cw", "tw", "death", "trump", "kill", "kms"]: 
            weight = 0

        # if a mention mentions someone else, increase its weight
        if "@" in word or word.lower() in ["david", "dayvid", "syc", "sycamore", "reed", "abi", "ethan"]: 
            weight *= 1.1
        
    if msg.channel.channel_id == 0: # boost chances of DMs being sent
        weight *= 1.1

    # penalize short messages, since they rarely are interesting. shorter messages get penalized more
    # will not penalize messages with pictures
    if word_count <= 5 and len(msg.attachments) == 0: 
        weight *= .1 * word_count

    # give a little boost to messages with pictures
    if len(msg.attachments) > 0:
        weight *= 1.2

    if "venting" in msg.channel.channel_name: # penalize messages in venting
        weight *= .3

    if "nsfw" in msg.channel.channel_name: # add a little spice for good measure
        weight *= 1.1

    if msg.sender.username in ["neonkitchens", "mineawesome", "insidioushumdrum", "anaru", "knifekeroppi"]: # prioritize messages sent by us
        weight *= 1.5

    if weight < 0: # negative number would break shit, and if the weight is 0 its impossible so
        return 0

    return weight

def getMessageFromToday() -> Message:
    messages_to_consider = []
    weights = []
    total_weight = 0

    today = date.today()
    this_year = today.year

    for year in range(2020, this_year):
        date_to_check = today.replace(year=year)
        if date_to_check in day_to_message:
            for message in day_to_message[date_to_check]:
                msg_weight = calcWeight(message)
                messages_to_consider.append(message)
                weights.append(msg_weight)
                total_weight += msg_weight
    
    message_choice = np.random.choice(messages_to_consider, 1, p=np.array(weights)/total_weight)

    return message_choice[0]

def getMessage(id: str) -> Message:
    global messages

    if id in messages:
        return messages[id]
    else:
        return None

def getOrPersistPerson(id: str, author_json: any) -> Person:
    global people

    if id in people:
        return people[id]
    
    username = author_json["name"]
    nickname = author_json["nickname"]
    color = author_json["color"]
    avatar = author_json["avatarUrl"]

    person = Person(username=username, discord_id=id, nickname=nickname, color=color, avatar=avatar)
    people[id] = person
    return person

def addMessageToDayMap(date: date, message: Message) -> None:
    global day_to_message

    if not date in day_to_message:
        day_to_message[date] = list[Message]()
    day_to_message[date].append(message)
    

allfiles = [join(getcwd(), 'messages2', f) for f in listdir(join(getcwd(), 'messages2')) if isfile(join(getcwd(), 'messages2', f))]

print("Parsing Files...")

for file in allfiles:
    print(f"Parsing {file}...")

    with open(file, "r") as jsonFile:
        data = json.load(jsonFile)
        guild_json = data['guild']
        channel_json = data['channel']

        current_channel = Channel(server_name=guild_json["name"], channel_name=channel_json["name"], icon=guild_json["iconUrl"], channel_id=channel_json["id"], server_id=guild_json["id"])

        channels[channel_json["id"]] = current_channel

        all_messages = data["messages"]

        for message_json in all_messages:
            author_json = message_json["author"]
            author_id = author_json["id"]
            author = getOrPersistPerson(author_id, author_json)

            content = message_json["content"]
            discord_id = message_json["id"]
            timestamp = datetime.fromisoformat(message_json["timestamp"])

            all_attachments = message_json["attachments"]
            attachments = list()

            for attachment_json in all_attachments:
                attachment_name = attachment_json["fileName"]
                attachment_url = attachment_json["url"]
                attachments.append(Attachment(attachment_url, attachment_name))

            message = Message(sender=author, channel=current_channel, content=content, ts=timestamp, discord_id=discord_id, attachments=attachments)
            message_date = timestamp.date()

            messages[discord_id] = message
            addMessageToDayMap(message_date, message)

print("Parsing Complete!")
