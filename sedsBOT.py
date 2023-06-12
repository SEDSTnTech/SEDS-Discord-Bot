from config import getToken
import os
import discord
import json
import time
import asyncio
from datetime import datetime, timedelta
from discord.ext import commands, tasks
import snscrape.modules.twitter as sn
import pandas as pd
import re
import random
import requests
from bs4 import BeautifulSoup

TOKEN = getToken()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='$', intents=intents)

botID = 1012850576335327445  # bot client id
welcomeChannelID = 386223930693779456
spaceNewsID = 504290552276058122
calendarInviteLink = "CALENDAR LINK HERE"
announcementsChannelID = 385870560439173131

global lastTweetID
lastTweetID = 0

global polls
polls = {}


@bot.event
async def on_ready():
    print("Hello")

def getTime():
    return datetime.now().strftime("[%Y-%m-%d/%H:%M:%S]")

global roleMsgID
with open("roleMessageID.json", "r") as jsonFile:
    roleMsgID = json.load(jsonFile)
    print(roleMsgID)

roleDict = {
    '📚': 'Members',
    '📜': 'Alumni',
    '🚀': 'Rocketry',
    '🛰️': 'CubeSat',
    '🔭': 'Radio',
    '🎈': 'Balloon Team',
    '💻': 'Software Team',
}



# **********************************************************
# ******************* Help *********************************
# **********************************************************

@bot.command()
async def botHelp(ctx):
    ctx.send("""
        Dont use this yet there arent enough commands to make this look cool""")


# **********************************************************
# ******************* Calendar *****************************
# **********************************************************

@bot.command()
async def calendarInvite(ctx):
    await ctx.author.send(f"Invite Link to the SEDS Google Calendar: {calendarInviteLink}")
    await ctx.message.delete()


# **********************************************************
# ********************* Polls ******************************
# **********************************************************

numDict = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟"
}

numEmojiDict = {  # remove this
    "1️⃣": 1,
    "2️⃣": 2,
    "3️⃣": 3,
    "4️⃣": 4,
    "5️⃣": 5,
    "6️⃣": 6,
    "7️⃣": 7,
    "8️⃣": 8,
    "9️⃣": 9,
    "🔟": 10
}


@bot.command()
async def test(ctx, arg1, arg2, arg3):
    await ctx.send(f"{arg1}, {arg2}, and {arg3}")

@bot.command()
async def purgePolls(ctx):
    polls = {}

@bot.command()
async def createPoll(ctx, channel: discord.TextChannel, limitVotes: bool, prompt, waitTime: int, *options):
    if len(polls) > 10:
        ctx.send("Warning: Number of saved polls is greater than 10, use command $purgePolls to erase all saved polls")
    curPollNum = len(polls)
    curPoll = {"msgID": 0,
               "votedList": [],
               "votesDict": {}}

    print(len(polls))
    polls[curPollNum] = curPoll
    if not limitVotes:
        polls[curPollNum]["votedList"] = None

    print(polls)
    pollText = ""
    for i, op in enumerate(options):
        pollText = pollText + f"{i + 1} - {op}\n"
    expTime = waitTime * 3600
    pollEmbed = discord.Embed(title=f"Poll: {prompt}",
                              description=f"{pollText}\nReact To Vote\nExpires in {waitTime} hours",
                              color=discord.Color.blue())
    pollMsg = await channel.send(embed=pollEmbed)

    pollMsgID = pollMsg.id
    polls[curPollNum]["msgID"] = pollMsgID
    print(polls)

    for i in range(1, len(options) + 1):
        polls[curPollNum]["votesDict"][i] = 0
        # votesDict[i] = 0
        await pollMsg.add_reaction(numDict[i])

    print(polls)
    await asyncio.sleep(expTime)  # change to *3600 and add removing reacts

    mostVotes = 0
    mostVotesIdx = 0
    ties = []
    votesDict = polls[curPollNum]["votesDict"]
    print("Votes for this poll:", votesDict)

    for i, votes in enumerate(votesDict.values()):  # add ties
        if votes == mostVotes:
            print("this is a tie")
            ties.append(options[i])

        elif votes > mostVotes:
            print(votes)
            mostVotes = votesDict[i+1]
            mostVotesIdx = i
            ties = [options[i]]

    if (len(ties) > 1) and mostVotes != 0:
        tieText = ""
        for tie in ties:
            tieText += tie + " / "
        finishedEmbed = discord.Embed(title="Poll Closed",
                                      description=f"There was a tie between the following: {tieText}",
                                      color=discord.Color.green())

    elif mostVotes != 0:
        finishedEmbed = discord.Embed(title="Poll Closed",
                                      description=f"'{options[mostVotesIdx]}' won with {mostVotes} votes",
                                      color=discord.Color.red())
    else:
        finishedEmbed = discord.Embed(title="Poll Closed", description="There were no winners because nobody voted!",
                                      color=discord.Color.green())

    await channel.send(embed=finishedEmbed)


@createPoll.error
async def createPoll_error(error, ctx):
    if isinstance(error, commands.ChannelNotFound):
        ctx.send("Channel Not Found")
    # elif isinstance(error, commands.Forbidden):
    #     ctx.send("I don't have access to that channel, check permissions and roles")


# **********************************************************
# ******************* Twitter ******************************
# **********************************************************


@tasks.loop(hours=6.0) # change to 24
async def getTweets():
    await bot.wait_until_ready()
    print(f"{getTime()} Searching for tweets\n")
    lastSearchDate = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") # change to days

    attributes_container = [] # might need to do something so tweets dont get posted
                                # twice with ids or smth, not sure yet, check if
                                # can check for tweets posted since a time
    for i, tweet in enumerate(sn.TwitterSearchScraper(f"(#space OR #spacenews OR #jameswebb OR from:nasa) -is:retweet min_faves:5000 lang:en since:{lastSearchDate}").get_items()): # change to 5000 or whatever likes minimum
        attributes_container.append([tweet.content, tweet.likeCount, tweet.user.username, tweet.date, tweet.url, tweet.id])

    tweets_df = pd.DataFrame(attributes_container, columns=["Tweet Content", "Number of Likes", "User", "Date", "Link", "ID"])
    print("Number of Newsworthy Tweets:",len(tweets_df))

    tweets_df.sort_values(by='ID', ascending=True, inplace=True)

    if (len(tweets_df) > 0):
        for index, row in tweets_df.iterrows():
            tweetText = row["Tweet Content"]

            global lastTweetID
            print(row["ID"])
            if row["ID"] > lastTweetID:
                await bot.get_channel(spaceNewsID).send(row["Link"])
                #attachedLink = re.search("(?P<url>https?://[^\s]+)", tweetText).group("url")

                lastTweetID = row["ID"]
                #await bot.get_channel(spaceNewsID).send(row["ID"])
                #if attachedLink is not None:
                    #await bot.get_channel(spaceNewsID).send(f"Attached Link: {attachedLink}")

            else:
                print("No new newsworthy tweets")
    else:
        print("No newsworthy tweets")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def startTweetLoop(ctx):
    getTweets.start()
    curDateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{getTime()} Tweet Loop Started\n")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def stopTweetLoop(ctx):
    getTweets.cancel()
    curDateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Tweet Loop Ended at {curDateTime}")


# **********************************************************
# ******************* Welcome ******************************
# **********************************************************

@bot.event
async def on_member_join(member):
#    guild_id = "379470440894169089"
#    guild = discord.utils.find(lambda g: g.id == guild_id, bot.guilds)
    guild = bot.get_guild(379470440894169089)
    print(guild)
    await member.send(
        f"Welcome {member.name} to the SEDS TnTech discord server! If you want to be able to view project channels, react with the corresponding emoji in the \#role-react channel. Also, please make your server nickname something similar to your actual name so that we know who's who. We hope to see you at the next meeting!")
    role = discord.utils.get(guild.roles, name='Members')
    await member.add_roles(role)

# **********************************************************
# ******************* Meetings *****************************
# **********************************************************

meetingMsgDict = {
    'first': '@everyone We will be having the first SEDS general meeting of the semester tonight in the Makerspace at 7pm!',

    'last': '@everyone We will be having the last SEDS general meeting of the semester tonight in the Makerspace at 7pm',

    'default': '@everyone We will be having our general meeting tonight at 7pm in the Makerspace',
    'prescott': '@everyone The meeting Tonight will be in Prescott 120 at 7pm',
    'cancelled': '@everyone The meeting tonight is cancelled'
}

global meetingMsgType
meetingMsgType = 'default'
meetingMsg = meetingMsgDict[meetingMsgType]


@tasks.loop(hours=168.0) # change to 24 and check day or 24*7
async def msgLoop():
    await bot.wait_until_ready()
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"Meeting loop triggered at {current_time}")

    # if ((datetime.today().weekday() == 1) or (datetime.today().weekday() == 2)):  # ---------------- change to 3 for wednesday
    global meetingMsgType
    await bot.get_channel(announcementsChannelID).send(meetingMsgDict[meetingMsgType])  # change to announcements chan

    if meetingMsgType != 'default':  # resets message to default after changing message
        meetingMsgType = 'default'


@bot.command()
@commands.has_permissions(manage_channels=True)  # add a reason to meeting cancelled, may need diff func
async def setMeetingMessage(ctx, msgType):
    global meetingMsgType
    if msgType in meetingMsgDict:
        meetingMsgType = msgType


@bot.command()
async def startMeetingMessageLoop(ctx, first=None):  # called to start the meeting message loop
    if (first is not None):
        global meetingMsgType
        meetingMsgType = 'first'

    msgLoop.start()


@bot.command()
async def stopMeetingMessageLoop(ctx):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"Message Loop stopped at {current_time}")
    msgLoop.cancel()

# **********************************************************
# ******************* Role React ***************************
# **********************************************************

@commands.has_permissions(manage_channels=True)
async def printRoles(channel: discord.TextChannel):

    roleText = ""
    for i, word in enumerate(roleDict):
        if i == 2:
            roleText = roleText + "\n"
        roleText = roleText + word + "   " + roleDict[word] + "\n"

    msg = await channel.send(roleText)
    global roleMsgID
    roleMsgID = msg.id

    with open("roleMessageID.json", "w") as jsonFile:
        json.dump(roleMsgID, jsonFile)

    for emoji in roleDict:
        await msg.add_reaction(emoji)


@bot.command()
@commands.has_permissions(manage_channels=True)
async def createRoleReact(ctx, channel: discord.TextChannel):
    await channel.send("React to get roles:")
    await printRoles(channel)


@createRoleReact.error
async def createRoleReact_error(error, ctx):
    if isinstance(error, discord.MissingPermissions):
        await ctx.send("You don't have permission to do that")


@bot.event
async def on_raw_reaction_add(payload):

    print("test")
    print(payload.message_id)
    if payload.user_id != botID:
        message_id = payload.message_id
        # channel = await bot.fetch_channel(payload.channel_id)
        isPoll = False
        pollNum = None
        for i, val in enumerate(polls):
            if message_id == polls[i]["msgID"]:
                isPoll = True
                pollNum = i

        if isPoll:

            curPoll = polls[pollNum]
            if polls[pollNum]["votedList"] is not None:
                if payload.member not in curPoll["votedList"]:
                    numChoice = numEmojiDict[payload.emoji.name]

                    polls[pollNum]["votesDict"][numChoice] += 1
                    print(polls)

                    polls[pollNum]["votedList"].append(payload.member)

                else:
                    print(polls)
                    print(f"{payload.member} tried to vote twice!")
            else:
                numChoice = numEmojiDict[payload.emoji.name]

                polls[pollNum]["votesDict"][numChoice] += 1
                print(polls)


        elif message_id == roleMsgID:
            role = None

            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, bot.guilds)

            if payload.emoji.name in roleDict:
                role = discord.utils.get(guild.roles,
                                            name=roleDict[payload.emoji.name])

            if role is not None:
                # member = discord.utils.find(lambda m: m.id == payload.user_id,
                #                             guild.members)
                member = payload.member

               # studentRole = discord.utils.get(guild.roles, name="Member")
               # alumniRole = discord.utils.get(guild.roles, name="Alumni")

               # if not ((role == studentRole and alumniRole in member.roles) or # was used so that you could only get the student or alumni role, but now student is assigned by default
               #         (role == alumniRole and studentRole in member.roles)):

                if member is not None:
                    await member.add_roles(role)
                    print("Added {} to {}".format(role, member))
                else:
                    print("Member '{}' not found".format(member))

            else:
                print("Role '{}' not found".format(role))


@bot.event
async def on_raw_reaction_remove(payload):

    print("test")
    message_id = payload.message_id
    print(message_id)
    role = None

    if (message_id == roleMsgID):
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, bot.guilds)

        if payload.emoji.name in roleDict:
            role = discord.utils.get(guild.roles,
                                     name=roleDict[payload.emoji.name])

        if role is not None:
            member = discord.utils.find(lambda m: m.id == payload.user_id,
                                        guild.members)
            # member = payload.member

            if member is not None:
                await member.remove_roles(role)
                print("Removed {} from {}".format(role, member))
            else:
                print("Member '{}' not found".format(member))
        else:
            print("Role '{}' not found".format(role))

@bot.command()
async def newRoleText(ctx):
    channel = bot.get_channel(1012122445542588586)
    msg = await channel.fetch_message("1012861673368985610")

    await msg.edit(content="""📚   Members
📜   Alumni

🚀   Rocketry
🛰️   CubeSat
🔭   Radio
🎈   Balloon Team
💻   Software Team""")

@bot.command()
async def addReactTemp(ctx):
    channel = bot.get_channel(1012122445542588586)
    msg = await channel.fetch_message("1012861673368985610")

    await msg.add_reaction('💻')


# **********************************************************
# ********************** Misc ******************************
# **********************************************************


@bot.command()
async def wiki(ctx):
    URL = "https://en.wikipedia.org/wiki/Special:Random"
    page = requests.get(URL)
    while (not page):
        page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")

    title = soup.find("h1", class_="firstHeading mw-first-heading")

    link_ext = title.text.replace(" ", "_")
    link = "https://en.wikipedia.org/wiki/" + link_ext

    try:
        page_test = requests.get(link)

    except:
        await ctx.send("Failed to get page at:", link)

    paragraph = soup.find_all("p")

    for p in paragraph:
        p = p.text.replace("\n", "")
        if (p.replace(" ", "") and p.replace("\n", "")):
            if (len(p) != 0):
                desc = p
                break

    embed = discord.Embed(title=title.text, url=link, description=desc)

    print(f"Getting page '{title.text}' at {link}")

    img = soup.find("a", class_="image")
    if (img):
        img = str(img).split(" ")
        for i in img:
            if ("src=\"" in i):
                i = i.replace("src=\"", "")
                img_url = i[:-1]
                img_url = "https:" + img_url
        embed.set_image(url=img_url)

    await ctx.send(embed=embed)

@bot.command(name='add')
async def _add(ctx, arg1: int, arg2: int):
    await ctx.send('{} + {} = {}'.format(arg1, arg2, arg1 + arg2))


@_add.error
async def add_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Can only add two integers")

bot.run(TOKEN)
