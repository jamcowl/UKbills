#!/usr/bin/env python

print "Importing libraries..."
import feedparser, sys, re, praw, time
print "Imports done."

# read login info and secret stuff from a file
loginFile='../redditBotLogins/ukBillsLogin.dat'
with open(loginFile,'r') as f:
	bot_user = f.readline().strip()
	bot_pass = f.readline().strip()
	bot_id = f.readline().strip()
	bot_secret = f.readline().strip()

# set up reddit script application with login info
reddit = praw.Reddit(client_id=bot_id,
		client_secret=bot_secret,
		password=bot_pass,
		user_agent='UKBills bot',
		username=bot_user)

# check connection and login success
print " > UKbills: Testing Reddit connection..."
username = str(reddit.user.me())
print " > UKbills: Logged in as /u/"+username

subreddit = reddit.subreddit('UKbills')

# get number 1-12 for bill status
def getProgress(fromHouse,currentHouse,stage):
	status = str(stage).lower()
	if status == "royal assent":
		return 12
	elif status == "consideration of amendments":
		return 11
	
	# count status
	progress = 1 # stage 1-12 (5 in each house, consideration of amendments, royal assent)
	if str(fromHouse) != str(currentHouse): # already gone through first house
		progress = progress + 5
	if status == "1st reading" or status == "first reading":
		return progress
	elif status == "2nd reading" or status == "second reading":
		return progress + 1
	elif status == "committee stage":
		return progress + 2
	elif status == "report stage":
		return progress + 3
	elif status == "3rd reading" or status == "third reading":
		return progress + 4
	else:
		return -1

# check if RSS update has been posted already
def hasBeenPosted(timeStamp,logFileName):
	logFile = open(logFileName,'r')
	for line in logFile:
		if str(line).strip() == str(timeStamp).strip():
			return True
	return False

#testfeed = """<?xml version="1.0" encoding="utf-8"?><rss xmlns:a10="http://www.w3.org/2005/Atom" version="2.0"><channel><title>Public Bills</title><link>http://services.parliament.uk/bills</link><description>A list of all public bills for the current session</description><item p4:stage="Report stage" xmlns:p4="urn:services.parliament.uk-bills.ext"><guid isPermaLink="true">http://services.parliament.uk/bills/2017-19/dataprotection.html</guid><link>http://services.parliament.uk/bills/2017-19/dataprotection.html</link><category>Lords</category><category>Government Bill</category><title>Data Protection</title><description>A Bill to make provision for the regulation of the processing of information relating to individuals; to make provision in connection with the Information Commissioner's functions under certain regulations relating to information; to make provision for a direct marketing code of conduct; and for connected purposes.</description><a10:updated>2017-11-03T18:05:44Z</a10:updated></item><item p4:stage="Committee stage" xmlns:p4="urn:services.parliament.uk-bills.ext"><guid isPermaLink="true">http://services.parliament.uk/bills/2017-19/europeanunionwithdrawal.html</guid><link>http://services.parliament.uk/bills/2017-19/europeanunionwithdrawal.html</link><category>Commons</category><category>Government Bill</category><title>European Union (Withdrawal)</title><description>A Bill to repeal the European Communities Act 1972 and make other provision in connection with the withdrawal of the United Kingdom from the EU.</description><a10:updated>2017-11-03T16:27:37Z</a10:updated></item><item p4:stage="Committee stage" xmlns:p4="urn:services.parliament.uk-bills.ext"><guid isPermaLink="true">http://services.parliament.uk/bills/2017-19/automatedandelectricvehicles.html</guid><link>http://services.parliament.uk/bills/2017-19/automatedandelectricvehicles.html</link><category>Commons</category><category>Government Bill</category><title>Automated and Electric Vehicles</title><description>A Bill to make provision about automated vehicles and electric vehicles.</description><a10:updated>2017-11-03T11:01:38Z</a10:updated></item><item p4:stage="Committee stage" xmlns:p4="urn:services.parliament.uk-bills.ext"><guid isPermaLink="true">http://services.parliament.uk/bills/2017-19/smartmeters.html</guid><link>http://services.parliament.uk/bills/2017-19/smartmeters.html</link><category>Commons</category><category>Government Bill</category><title>Smart Meters</title><description>A Bill to extend the period for the Secretary of State to exercise powers relating to smart metering and to provide for a special administration regime for a smart meter communication licensee.</description><a10:updated>2017-11-03T10:20:53Z</a10:updated></item></channel></rss>"""
#feed = feedparser.parse(testfeed)

# read RSS feed
url = 'https://services.parliament.uk/bills/AllPublicBills.rss'
logFileName = 'postHistory.log'
feed = feedparser.parse(url)
while(True):
	for item in feed.entries:
		billName = item['description']
		if billName.lower().startswith("to "):
			billName = billName[0].upper()+billName[1:]
		elif billName.lower().startswith("a bill to "):
			billName = billName[7:]
			billName = billName[0].upper()+billName[1:]
		link = item['link']
		currentHouse = item['category'] # which house it's currently in
		timeStamp = item['updated']
		if hasBeenPosted(timeStamp,logFileName):
			print " > UKbills: Already posted "+timeStamp+", moving on..."
			continue
		fromHouse = "Commons" # assume from commons unless found otherwise
		docslink = re.sub(".html","/documents.html",link)
		rsslink = re.sub("/bills/20.*/","/bills/RSS/",link)
		rsslink = re.sub(".html",".xml",rsslink)
		subfeed = feedparser.parse(rsslink)
		latestUpdate = subfeed.entries[0]
		stage = latestUpdate['stage']
				
		# check if it was started in the Lords
		if "[HL]" in latestUpdate['description']:
			fromHouse = "Lords"
		
		# find progress level
		progress = getProgress(fromHouse,currentHouse,stage)
		info = "[Stage "+str(progress)+"/12]["+currentHouse+", "+stage+"] "+billName
		if len(info) > 300:
			info = info[:298]+".."

		# create comment text with document info
		extraInfo = "Documents relating to this bill are available [here]("+docslink+")."
#		print "About to submit..."
#		print info
#		print link
#		print extraInfo
#		print " >>>> I WOULD HAVE POSTED TO REDDIT"
		submission = subreddit.submit(info,url=link)
		comment = submission.reply(extraInfo)
		commentmod = praw.models.reddit.comment.CommentModeration(comment)
		commentmod.distinguish(how='yes', sticky=True)
		print " > UKbills: posted to subreddit: "+info
		raw_input("should I continue?")
		
		outputFile = open(logFileName,'a')
		outputFile.write(timeStamp+"\n")
		outputFile.close()
	
	for i in range(5,0,-1):
		print " > UKbills: Waiting "+str(i)+" minutes..."
		time.sleep(60)
