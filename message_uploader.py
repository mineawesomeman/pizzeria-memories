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

def channelToDict(channel: mr.Channel) -> dict[str, any]:
    out = dict()

    out["server_name"] = channel.server_name
    out["channel_name"] = channel.channel_name
    out["icon"] = channel.icon
    out["channel_id"] = channel.channel_id
    out["server_id"] = channel.server_id
    
    return out

def personToDict(person: mr.Person) -> dict[str, any]:
    out = dict()

    out["username"] = person.username
    out["discord_id"] = person.discord_id
    out["nickname"] = person.nickname
    out["color"] = person.color
    out["avatar"] = person.avatar

    return out

def messageToDict(message: mr.Message) -> dict[str, any]:
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


print("uploading channels")

for channel_id in mr.channels:
    channel = mr.channels[channel_id]
    print(f"found channel {channel.channel_name}")

    channel_dict = channelToDict(channel)

    channels.add(channel_dict, channel_id)

print("uploading people")

for person_id in mr.people:
    person = mr.people[person_id]
    print(f"found person {person.username}")

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