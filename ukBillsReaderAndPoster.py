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

# input/output
url = 'https://services.parliament.uk/bills/AllPublicBills.rss'
logFileName = 'postHistory.log'

# permanent loop
while(True):
	try:
		feed = feedparser.parse(url)
		
		# loop over entries in RSS feed:
		for item in feed.entries:
			
			# get bill name and tidy it
			billName = item['description']
			if billName.lower().startswith("to "):
				billName = billName[0].upper()+billName[1:]
			elif billName.lower().startswith("a bill to "):
				billName = billName[7:]
				billName = billName[0].upper()+billName[1:]
			
			# get other bill info
			link = item['link']
			currentHouse = item['category'] # which house it's currently in
			timeStamp = item['updated']
			fromHouse = "Commons" # assume from commons unless found otherwise
			
			# check if posted already
			if hasBeenPosted(timeStamp,logFileName):
				print " > UKbills: Already posted update from "+timeStamp+", moving on..."
				continue
			
			# get links
			docslink = re.sub(".html","/documents.html",link)
			stageslink = re.sub(".html","/stages.html",link)
			rsslink = re.sub("/bills/20.*/","/bills/RSS/",link)
			rsslink = re.sub(".html",".xml",rsslink)

			# read specific RSS feed for bill
			subfeed = feedparser.parse(rsslink)
			latestUpdate = subfeed.entries[0]
			
			# find progress level
			stage = latestUpdate['stage']
			if "[HL]" in latestUpdate['description']: # check if it was started in the Lords
				fromHouse = "Lords"
			progress = getProgress(fromHouse,currentHouse,stage)
                        if progress < 0: # progress bugged out
                                print " > UKbills: stage '"+str(stage)+"' unknown, skipping for now and will retry next time."
                                continue
                
			# construct post title
			info = "[Stage "+str(progress)+"/12]["+currentHouse+", "+stage+"] "+billName
			if len(info) > 300:
				info = info[:298]+".."
	
			# create comment text with document info
			extraInfo = "A timeline of this bill's stages is available [here]("+stageslink+")."
			extraInfo = extraInfo+"\n\n"
			extraInfo = extraInfo+"Documents relating to this bill are available [here]("+docslink+")."
	
			# submit to the subreddit
			submission = subreddit.submit(info,url=link)

			# record this update as already posted
			outputFile = open(logFileName,'a')
			outputFile.write(timeStamp+"\n")
			outputFile.close()

                        # post supplementary comment info
                        comment = submission.reply(extraInfo)
			commentmod = praw.models.reddit.comment.CommentModeration(comment)
			commentmod.distinguish(how='yes', sticky=True)
			print " > UKbills: posted to subreddit: "+info
			#raw_input(" > UKbills: Paused. Press any key to continue.")

	# catch bugs and try again
	except Exception, e:
		print " > UKbills: Got an error: "+str(e)
		print " > UKbills: Trying again..."
		continue

	# done checking for updates, wait 15 mins and look again
	for i in range(15,0,-1):
		print " > UKbills: Waiting "+str(i)+" minutes..."
		time.sleep(60)
		
	print " > UKbills: looping round again..."

