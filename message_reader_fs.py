from datetime import *
from google.cloud import firestore
import google.auth as auth
import numpy as np
import pytz
from readerwriterlock.rwlock import RWLockWrite

creds, project_id = auth.load_credentials_from_file("service-account-auth.json")

print("authing")
db = firestore.Client(project=project_id, credentials=creds)

channels = db.collection("servers", "pizzeria", "channels")
people = db.collection("servers", "pizzeria", "people")
messages = db.collection("servers", "pizzeria", "messages")

EDT = pytz.timezone('US/Eastern')

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

todays_messages = set[Message]()
date_of_todays_messages = date(1, 1, 1)
tm_lock = RWLockWrite()

def getMessages() -> tuple[set[Message], date]:
    global tm_lock
    global todays_messages
    global date_of_todays_messages

    with tm_lock.gen_rlock():
        return todays_messages, date_of_todays_messages

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
    all_messages, all_messages_date = getMessages()

    messages_to_consider = []
    weights = []
    total_weight = 0

    if all_messages_date != date.today():
        updateTodaysMessages()
    for message in all_messages:
        msg_weight = calcWeight(message)
        messages_to_consider.append(message)
        weights.append(msg_weight)
        total_weight += msg_weight
    
    message_choice = np.random.choice(messages_to_consider, 1, p=np.array(weights)/total_weight)

    return message_choice[0]

def getMessage(id: str) -> Message | None:
    try:
        return loadMessage(db.document("servers", "pizzeria", "messages", id).get())
    except:
        return None

def loadMessage(docsnap: firestore.DocumentSnapshot) -> Message:
    sendsnap: firestore.DocumentSnapshot = docsnap.get("sender").get()
    chansnap: firestore.DocumentSnapshot = docsnap.get("channel").get()

    sender_username: str = sendsnap.get("username")
    sender_id: str = sendsnap.get("discord_id")
    sender_nickname: str = sendsnap.get("nickname")
    sender_color: str = sendsnap.get("color")
    sender_avatar: str = sendsnap.get("avatar")

    sender = Person(sender_username, sender_id, sender_nickname, sender_color, sender_avatar)

    channel_server_name: str = chansnap.get("server_name")
    channel_name: str = chansnap.get("channel_name")
    channel_icon: str = chansnap.get("icon")
    channel_id: str = chansnap.get("channel_id")
    channel_server_id: str = chansnap.get("server_id")

    channel = Channel(channel_server_name, channel_name, channel_icon, channel_id, channel_server_id)

    content: str = docsnap.get("content")
    ts: datetime = docsnap.get("ts").astimezone(EDT)
    discord_id: str = docsnap.get("discord_id")
    attachments = []

    for attach_data in docsnap.get("attachments"):
        att_name = attach_data["name"]
        att_url = attach_data["url"]

        attachment = Attachment(att_url, att_name)
        attachments.append(attachment)
    
    return Message(sender, channel, content, ts, discord_id, attachments)

def updateTodaysMessages() -> None:
    global tm_lock
    with tm_lock.gen_wlock():
        global todays_messages
        global date_of_todays_messages

        if date_of_todays_messages == date.today():
            return

        today = date.today()
        todays_messages = set[Message]()
        date_of_todays_messages = today

        for year in range(2020, today.year):
            start = datetime(year, today.month, today.day, 0, 0, 0, 0, EDT)
            end = datetime(year, today.month, today.day, 23, 59, 59, 999999, EDT)

            query = messages.where(filter=firestore.FieldFilter("ts", ">=", start)).where(filter=firestore.FieldFilter("ts", "<=", end)).limit(1000)

            docs = query.get()

            for doc in docs:
                docobj = loadMessage(doc)
                todays_messages.add(docobj)

print("initializing message cache")
updateTodaysMessages()
print("message reader ready")