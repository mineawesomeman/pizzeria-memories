from google.cloud import firestore
import google.auth as auth
import datetime as dt
import message_reader as mr

creds, project_id = auth.load_credentials_from_file("service-account-auth.json")

print("authing")
db = firestore.Client(project=project_id, credentials=creds)

channels = db.collection("servers", "pizzeria", "channels")
people = db.collection("servers", "pizzeria", "people")
messages = db.collection("servers", "pizzeria", "messages")

def channelToDict(channel: mr.Channel) -> dict[str, str]:
    out = dict()

    out["server_name"] = channel.server_name
    out["channel_name"] = channel.channel_name
    out["icon"] = channel.icon
    out["channel_id"] = channel.channel_id
    out["server_id"] = channel.server_id
    
    return out

def personToDict(person: mr.Person) -> dict[str, str]:
    out = dict()

    out["username"] = person.username
    out["discord_id"] = person.discord_id
    out["nickname"] = person.nickname
    out["color"] = person.color
    out["avatar"] = person.avatar

    return out

def messageToDict(message: mr.Message) -> dict[str, str]:
    out = dict()

    out["sender"] = db.document("servers", "pizzeria", "people", message.sender.discord_id)
    out["channel"] = db.document("servers", "pizzeria", "channels", message.channel.channel_id)
    out["content"] = message.content
    out["ts"] = message.ts
    out["discord_id"] = message.discord_id

    attachments = []

    for attachment in message.attachments:
        att_out = dict()
        
        att_out["url"] = attachment.url
        att_out["name"] = attachment.name

        attachments.append(att_out)
    
    out["attachments"] = attachments

    return out

def loadPerson(docsnap: firestore.DocumentSnapshot) -> mr.Person:
    person_username: str = docsnap.get("username")
    person_id: str = docsnap.get("discord_id")
    person_nickname: str = docsnap.get("nickname")
    person_color: str = docsnap.get("color")
    person_avatar: str = docsnap.get("avatar")

    return mr.Person(person_username, person_id, person_nickname, person_color, person_avatar)

def loadChannel(docsnap: firestore.DocumentSnapshot) -> mr.Channel:
    channel_server_name: str = docsnap.get("server_name")
    channel_name: str = docsnap.get("channel_name")
    channel_icon: str = docsnap.get("icon")
    channel_id: str = docsnap.get("channel_id")
    channel_server_id: str = docsnap.get("server_id")

    return mr.Channel(channel_server_name, channel_name, channel_icon, int(channel_id), int(channel_server_id))

print("uploading channels")

for channel_id in mr.channels:
    channel = mr.channels[channel_id]
    print(f"found channel {channel.channel_name}")

    channelref = db.document("servers", "pizzeria", "channels", channel_id)
    channelsnap = channelref.get()

    if channelsnap.exists:
        # we only check icon, channel_name, and server_name since its the only things that would change
        loadedchannel = loadChannel(channelsnap)

        if channel.channel_name != loadedchannel.channel_name:
            channelref.update({"channel_name": channel.channel_name})
        
        if channel.server_name != loadedchannel.server_name:
            channelref.update({"server_name": channel.server_name})

        if channel.icon != loadedchannel.icon:
            channelref.update({"icon": channel.icon})
    else:
        channel_dict = channelToDict(channel)
        channels.add(channel_dict, channel_id)

print("uploading people")

for person_id in mr.people:
    person = mr.people[person_id]
    print(f"found person {person.username}")

    senderref = db.document("servers", "pizzeria", "people", person_id)
    sendersnap = senderref.get()
    
    if sendersnap.exists:
        # we only check nickname, avatar, and color since those change
        loadedperson = loadPerson(sendersnap)

        if person.nickname != loadedperson.nickname:
            senderref.update({"nickname": person.nickname})
        
        if person.avatar != loadedperson.avatar:
            senderref.update({"avatar": person.avatar})
        
        if person.color != loadedperson.color:
            senderref.update({"color": person.color})
    else:
        person_dict = personToDict(person)
        people.add(person_dict, person_id)

print("uploading messages (this will take a while!)")
message_count = len(mr.messages)

for i, message_id in enumerate(mr.messages):
    message = mr.messages[message_id]
    if i % 1000 == 0:
        print(f"uploading message {i}/{message_count}")

    message_dict = messageToDict(message)
    messages.add(message_dict, message_id)

db.close()