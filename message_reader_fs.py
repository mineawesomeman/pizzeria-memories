from datetime import *
from google.cloud import firestore
import google.auth as auth
import numpy as np
import pytz
import random
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
    
    def toDict(self) -> dict[str, any]:
        out = dict()

        out["server_name"] = self.server_name
        out["channel_name"] = self.channel_name
        out["icon"] = self.icon
        out["channel_id"] = self.channel_id
        out["server_id"] = self.server_id
        
        return out

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
    
    def toDict(self) -> dict[str, any]:
        out = dict()

        out["username"] = self.username
        out["discord_id"] = self.discord_id
        out["nickname"] = self.nickname
        out["color"] = self.color
        out["avatar"] = self.avatar

        return out

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
    
    def toDict(self) -> dict[str, any]:
        out = dict()

        out["sender"] = db.document("servers", "pizzeria", "people", self.sender.discord_id)
        out["channel"] = db.document("servers", "pizzeria", "channels", self.channel.channel_id)
        out["content"] = self.content
        out["ts"] = self.ts
        out["discord_id"] = self.discord_id

        attachments = []

        for attachment in self.attachments:
            att_out = dict()
            
            att_out["url"] = attachment.url
            att_out["name"] = attachment.name

            attachments.append(att_out)
        
        out["attachments"] = attachments

        return out

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

def putMessage(message: Message):
    channelref = db.document("servers", "pizzeria", "channels", message.channel.channel_id)
    channelsnap = channelref.get()

    if channelsnap.exists:
        # only do it 1 out of every 5 messages
        if random.randrange(0,5) == 0:
            # we only check icon, channel_name, and server_name since its the only things that would change
            channel = loadChannel(channelsnap)

            if channel.channel_name != message.channel.channel_name:
                channelref.update({"channel_name": message.channel.channel_name})
            
            if channel.server_name != message.channel.server_name:
                channelref.update({"server_name": message.channel.server_name})

            if channel.icon != message.channel.icon:
                channelref.update({"icon": message.channel.icon})
    else:
        channels.add(message.channel.toDict(), message.channel.channel_id)
    
    senderref = db.document("servers", "pizzeria", "people", message.sender.discord_id)
    sendersnap = senderref.get()
    
    if sendersnap.exists:
        # we only do this on 1 out of every 5 messages
        if random.randrange(0,5) == 0:
            # we only check nickname, avatar, and color since those change
            person = loadPerson(sendersnap)

            if person.nickname != message.sender.nickname:
                senderref.update({"nickname": message.sender.nickname})
            
            if person.avatar != message.sender.avatar:
                senderref.update({"avatar": message.sender.avatar})
            
            if person.color != message.sender.color:
                senderref.update({"color": message.sender.color})
    else:
        people.add(message.sender.toDict(), message.sender.discord_id)

    messages.add(message.toDict(), message.discord_id)

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

    sender = loadPerson(sendsnap)
    channel = loadChannel(chansnap)

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

def loadPerson(docsnap: firestore.DocumentSnapshot) -> Person:
    person_username: str = docsnap.get("username")
    person_id: str = docsnap.get("discord_id")
    person_nickname: str = docsnap.get("nickname")
    person_color: str = docsnap.get("color")
    person_avatar: str = docsnap.get("avatar")

    return Person(person_username, person_id, person_nickname, person_color, person_avatar)

def loadChannel(docsnap: firestore.DocumentSnapshot) -> Channel:
    channel_server_name: str = docsnap.get("server_name")
    channel_name: str = docsnap.get("channel_name")
    channel_icon: str = docsnap.get("icon")
    channel_id: str = docsnap.get("channel_id")
    channel_server_id: str = docsnap.get("server_id")

    return Channel(channel_server_name, channel_name, channel_icon, channel_id, channel_server_id)

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