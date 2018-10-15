import datetime
from datetime import timedelta
from selenium import webdriver
from slackclient import SlackClient
from config import *
import json
import time
import sys

loggedData = {}
# list of names which when scraped should be ignored
blacklist = []

#Uses selinium to open a browser, go to the USEED leaderboard and paese
# through it to gather each persons name and associated email address.
#Returns an array of dictionaries containing each persons name and number
# of emails sent at the current time.
def getData():
    print("Logging in to USEED")

    loginURL = "https://uw.useed.net/users/sign_in"
    uname = usr_name
    pwd = usr_password

    browser = webdriver.Chrome(executable_path=r".\chromedriver.exe") #replace with .Firefox(), or with the browser of your choice
    url = loginURL
    browser.get(url) #navigate to the page

    username = browser.find_element_by_id("user_email") #username form field
    password = browser.find_element_by_id("user_password") #password form field

    username.send_keys(uname)
    password.send_keys(pwd)

    submitButton = browser.find_element_by_class_name("btn")
    submitButton.click()

    browser.get("https://uw.useed.net/dashboard/projects/1012/home")

    table = browser.find_element_by_id("leaderboard");
    tableRows = table.find_elements_by_tag_name("tr");
    print("Retrieving data.")
    for x in tableRows:
        individual = x.find_elements_by_tag_name("td")
        temp = 0
        key = ""
        value = ""
        for y in individual:
            if temp == 1:
                key = y.text
            if temp == 5:
                value = y.text
            temp = temp + 1;
        loggedData[key] = {"name":key, "emails":value}
    browser.close()
    return loggedData

#outputs most recent logged data to a logfile
def log():
    loggedData = getData();
    print("Data has been recieved")
    date = datetime.date.today()
    date_s = date.strftime("%m-%d-%Y")
    print("Saving to outfile: " + date_s + ".txt")
    with open("logs/"+date_s + '.txt', 'w') as outfile:
        json.dump(loggedData, outfile, indent=4)

#generates a list of flagged individuals who are below the perscribed email quota.
def check():
    loggedData = getData();
    date = datetime.date.today()
    day = timedelta(days=1)
    week = timedelta(days=7)
    with open("logs/namelist.txt", "r") as infile:
        namelist = json.load(infile)
    with open("logs/slack_unames.txt", "r") as infile:
        slackID = json.load(infile)
    with open("logs/02-09-2018.txt", "r") as infile:
        oneweekago = json.load(infile)
    emailStats = {}
    print("Comparing with historical data.")
    for x in namelist:
        lastWeek = int(loggedData[x]["emails"]) - int(oneweekago[x]["emails"])
        emailStats[loggedData[x]["name"]] = {
            'lastWeek': lastWeek,
            'underQuota':(5 > lastWeek),
            'slackID': slackID[x]
        }
    notify = {}
    for x in namelist:
        if (emailStats[x]['underQuota']):
            notify[x] = emailStats[x]
    print("Printing result to outfile")
    #Only necessary for saving diagnostic data
    with open('emailStats.txt', 'w') as outfile:
        json.dump(emailStats, outfile, indent=4)
    with open('notify.txt', 'w') as outfile:
        json.dump(notify, outfile, indent=4)

#Pretty much does everything. Logs and check against most recent logs and then sends messages automatically.
def slack():
    log()
    check()
    with open("logs/namelist.txt", "r") as infile:
        namelist = json.load(infile)
    with open('notify.txt', "r") as infile:
        notify = json.load(infile)
    slack_token = api_token
    sc = SlackClient(slack_token)
    slackID = "";
    confirm = input("Are you sure you want to send slack messages to " + str(len(notify)) + " people? (y/n)")
    if (confirm.lower() == 'y'):
        msg = input("What message do you want to send?: ");
        count = 0
        for i in namelist:
            if (i in notify):
                count = count + 1
                print("Sending message " + str(count) + " of " + str(len(notify)))
                sc.api_call(
                  "chat.postMessage",
                  channel= notify[i]['slackID'],
                  text= msg
                )
                time.sleep(1)
    else:
        print("Send aborted")

#Generates list of names from data parsed from the USEED website. This list is
# used to iterate through the dictionaries.
def genNameList():
    with open("logs/nameBackData.txt", "r") as infile:
        onedayago = json.load(infile)
    emailStat = []
    for x in range(1, len(onedayago)):
        if(not(onedayago[x]["name"] in blacklist)):
            emailStat.append(onedayago[x]["name"])
    with open('namelist.txt', 'w') as outfile:
        json.dump(emailStat, outfile, indent=4)

#Temp method used to automate data transfer
def slacknamelistgen():
    slack_unames = {}
    with open("logs/namelist.txt", "r") as infile:
        namelist = json.load(infile)
    for i in namelist:
        slack_unames[i] = input("What is " + i + " slack username: ")
    with open('slack_unames.txt', 'w') as outfile:
        json.dump(slack_unames, outfile, indent=4)

#processes CLI arguments. Replace with gathering user input in further work
if (len(sys.argv) < 2):
    text = input("What is the desired task(\"check\" or \"log\" or \"slack\"): ")
    if (text.lower() == 'log'):
        log()
    elif (text.lower() == 'check'):
        check()
    elif (text.lower() == 'slack'):
        slack()
    else:
        print("Invalid input arguments: try \"check\" of \"log\" for better results")
else:
    if (sys.argv[1].lower() == 'log'):
        log()
    elif (sys.argv[1].lower() == 'check'):
        check()
    elif (sys.argv[1].lower() == 'namelist'):
        genNameList()
    elif (sys.argv[1].lower() == 'slackgen'):
        slacknamelistgen()
    else:
        print("Invalid input arguments: try \"check\" of \"log\" for better results")
