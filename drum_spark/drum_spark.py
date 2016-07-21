#! /usr/bin/python

__author__ = 'cpuskarz'


# ToDo - Method to monitor incoming 1 on 1 messages

from flask import Flask, request, Response
import requests, json, re

app = Flask(__name__)

spark_host = "https://api.ciscospark.com/"
spark_headers = {}
spark_headers["Content-type"] = "application/json"
app_headers = {}
app_headers["Content-type"] = "application/json"

@app.route('/', methods=["POST"])
def process_webhook():
    # Verify that the request is propery authorized
    # authz = valid_request_check(request)
    # if not authz[0]:
    #     return authz[1]

    post_data = request.get_json(force=True)
    # pprint(post_data)

    # Check what room this came from
    # If Demo Room process for open room
    if post_data["data"]["roomId"] == demo_room_id:
        #print("Incoming Demo Room Message.")
        sys.stderr.write("Incoming Demo Room Message\n")
        process_demoroom_message(post_data)
        #message_id = post_data["data"]["id"]
        #message = get_message(message_id)
        #pprint(message)
        
        #if message["text"].lower().find("results") > -1:
        #    results = get_results()
        #    reply = "The current standings are\n"
        #    for result in results:
        #        reply += "  - %s has %s votes.\n" % (result[0], result[1])
        #elif message["text"].lower().find("options") > -1:
        #    options = get_options()
        #    reply = "The options are... \n"
        #    for option in options:
        #        reply += "  - %s \n" % option
        #elif message["text"].lower().find("vote") > -1:
        #    reply = "Let's vote!  Look for a new message from me so you can place a secure vote!"
        #    start_vote_session(message["personEmail"])
        #else:
            # Reply back to message
        #   reply = "Hello, welcome to the Drummer Demo Room.\n" \
        #            "To find out current status of voting, ask 'What are the results?'\n" \
        #            "To find out the possible options, ask 'What are the options?\n" \
        #            '''To place a vote, say "I'd like to vote" to start a private voting session.'''
        #    send_message_to_room(demo_room_id, reply)
        # If not the demo room, assume its a user voting session
        break
    else:
        # print("Incoming Individual Message.")
        sys.stderr.write("Incoming Individual Message\n")
        process_incoming_message(post_data)

    return ""

@app.route("/demoroom/members", methods=["PUT", "GET"])
def process_demoroom_members():
    # Verify that the request is propery authorized
    #authz = valid_request_check(request)
    #if not authz[0]:
    #    return authz[1]

    status = 200
    if request.method == "PUT":
        data = request.get_json(force=True)
        try:
            sys.stderr.write("Adding %s to demo room.\n" % (data["email"]))
            add_email_demo_room(data["email"], demo_room_id)
            status = 201
        except KeyError:
            error = {"Error":"API Expects dictionary object with single element and key of 'email'"}
            status = 400
            resp = Response(json.dumps(error), content_type='application/json', status=status)
            return resp

    demo_room_members = get_membership_for_room(demo_room_id)
    resp = Response(
        json.dumps(demo_room_members, sort_keys=True, indent = 4, separators = (',', ': ')),
        content_type='application/json',
        status=status)

    return resp


# Bot functions to process the incoming messages posted by Cisco Spark
def process_demoroom_message(post_data):
    message_id = post_data["data"]["id"]
    message = get_message(message_id)
    # pprint(message)

    # First make sure not processing a message from the bot
    if message["personEmail"] == bot_email:
        return ""


    # Check if message contains word "results" and if so send results
    if message["text"].lower().find("results") > -1:
        results = get_results()
        reply = "The current standings are\n"
        for result in results:
            reply += "  - %s has %s votes.\n" % (result[0], result[1])
    # Check if message contains word "options" and if so send options
    elif message["text"].lower().find("options") > -1:
        options = get_options()
        reply = "The options are... \n"
        for option in options:
            reply += "  - %s \n" % option
    # Check if message contains word "vote" and if so start a voting session
    elif message["text"].lower().find("vote") > -1:
        reply = "Let's vote!  Look for a new message from me so you can place a secure vote!"
        start_vote_session(message["personEmail"])
    # Check if message contains phrase "add email" and if so add user to room
    elif message["text"].lower().find("add email") > -1:
        # Get the email that comes
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', message["text"])
        # pprint(emails)
        reply = "Adding users to demo room.\n"
        for email in emails:
            add_email_demo_room(email, demo_room_id)
            reply += "  - %s \n" % (email)
    # If nothing matches, send instructions
    else:
        # Reply back to message
        reply = "Hello, welcome to the Chet Drummer World Demo Room.\n" \
                "To find out current status of voting, ask 'What are the results?'\n" \
                "To find out the possible options, ask 'What are the options?\n" \
                '''To place a vote, say "I'd like to vote" to start a private voting session.'''

    send_message_to_room(demo_room_id, reply)


# For when a user wants to vote
# 1.  Reply in demo room
# 2.  Send Message to Sender
# 3.  Setup WebHook to room with sender
def start_vote_session(email):
    options = get_options()
    intro = "Thanks for taking time to vote for your favorite drummer. \n" \
            "To vote simply type the name of your drummer in a message. \n" \
            "Options are: "
    for option in options:
        intro += "  - %s \n" % (option)

    message = send_message_to_email(email, intro)
    # pprint(message)

    # Setup WebHook with person
    webhook = setup_webhook(message["roomId"], bot_url, "Webhook for " + email)
    return ""

# This typically indicates a message in an active voting session
def process_incoming_message(post_data):
    # pprint(post_data)

    webhook_id = post_data["id"]
    room_id = post_data["data"]["roomId"]

    message_id = post_data["data"]["id"]
    message = get_message(message_id)
    # pprint(message)

    # First make sure not processing a message from the bot
    if message["personEmail"] == bot_email:
        return ""

    # What to do...
    # 1.  Get Possible Options
    # 2.  See if the message contains one of the options
    # 3.  Cast vote for option
    # 4.  Thank the user for their vote
    # 5.  Delete Webhook

    options = get_options()
    chosen_hero = ""
    for option in options:
        if message["text"].lower().find(option.lower()) > -1:
            sys.stderr.write("Found a vote for: " + option + "\n")
            chosen_hero = option
            break

    # Cast Vote
    if chosen_hero != "":
        vote = place_vote(chosen_hero)
        delete_webhook(webhook_id)
        msg = "Thanks for your vote for %s.  Your vote has been recorded and this ends this voting session." % (chosen_hero)
        send_message_to_email(message["personEmail"], msg)
    else:
        msg = "I didn't understand your vote, please type the name of your chosen hero exactly as listed on the ballot.  "
        send_message_to_email(message["personEmail"], msg)
    return ""

# Utilities to interact with the MyHero-App Server
def get_results():
    u = app_server + "/results"
    page = requests.get(u, headers = app_headers)
    tally = page.json()
    tally = sorted(tally.items(), key = lambda (k,v): v, reverse=True)
    return tally

def get_options():
    u = app_server + "/options"
    page = requests.get(u, headers=app_headers)
    options = page.json()["options"]
    return options
'''
def place_vote(vote):
    u = app_server + "/vote/" + vote
    page = requests.post(u, headers=app_headers)
    return page.json()
'''

# MyHero Demo Room Setup
def setup_demo_room():
    rooms = current_rooms()
    # pprint(rooms)

    # Look for a room called "MyHero Demo"
    demo_room_id = ""
    for room in rooms:
        if room["title"] == "Drummer World":
            # print("Found Room")
            demo_room_id = room["id"]
            break

    # If demo room not found, create it
    if demo_room_id == "":
        demo_room = create_demo_room()
        demo_room_id = demo_room["id"]
        # pprint(demo_room)

    return demo_room_id

def create_demo_room():
    spark_u = spark_host + "v1/rooms"
    spark_body = {"title":"Drummer World"}
    page = requests.post(spark_u, headers = spark_headers, json=spark_body)
    print "IN CREATE DEMO ROOM"
    print page
    room = page.json()
    return room

# Utility Add a user to the MyHero Demo Room
def add_email_demo_room(email, room_id):
    spark_u = spark_host + "v1/memberships"
    spark_body = {"personEmail": email, "roomId" : room_id}
    page = requests.post(spark_u, headers = spark_headers, json=spark_body)
    membership = page.json()
    return membership


# Spark Utility Functions
#### Message Utilities
def send_message_to_email(email, message):
    spark_u = spark_host + "v1/messages"
    message_body = {
        "toPersonEmail" : email,
        "text" : message
    }
    page = requests.post(spark_u, headers = spark_headers, json=message_body)
    message = page.json()
    return message

def send_message_to_room(room_id, message):
    spark_u = spark_host + "v1/messages"
    message_body = {
        "roomId" : room_id,
        "text" : message
    }
    page = requests.post(spark_u, headers = spark_headers, json=message_body)
    message = page.json()
    return message

def get_message(message_id):
    spark_u = spark_host + "v1/messages/" + message_id
    page = requests.get(spark_u, headers = spark_headers)
    message = page.json()
    return message

#### Webhook Utilities
def current_webhooks():
    spark_u = spark_host + "v1/webhooks"
    page = requests.get(spark_u, headers = spark_headers)
    webhooks = page.json()
    return webhooks["items"]

def create_webhook(roomId, target, webhook_name = "New Webhook"):
    spark_u = spark_host + "v1/webhooks"
    spark_body = {
        "name" : webhook_name,
        "targetUrl" : target,
        "resource" : "messages",
        "event" : "created",
        "filter" : "roomId=" + roomId
    }
    page = requests.post(spark_u, headers = spark_headers, json=spark_body)
    webhook = page.json()
    return webhook

def update_webhook(webhook_id, target, name):
    spark_u = spark_host + "v1/webhooks/" + webhook_id
    spark_body = {
        "name" : name,
        "targetUrl" : target
    }
    page = requests.put(spark_u, headers = spark_headers, json=spark_body)
    webhook = page.json()
    return webhook

def delete_webhook(webhook_id):
    spark_u = spark_host + "v1/webhooks/" + webhook_id
    page = requests.delete(spark_u, headers = spark_headers)

def setup_webhook(room_id, target, name):
    webhooks = current_webhooks()
    # pprint(webhooks)

    # Look for a Web Hook for the Room
    webhook_id = ""
    for webhook in webhooks:
        if webhook["filter"] == "roomId=" + room_id:
            # print("Found Webhook")
            webhook_id = webhook["id"]
            break

    # If Web Hook not found, create it
    if webhook_id == "":
        webhook = create_webhook(room_id, target, name)
        webhook_id = webhook["id"]
    # If found, update url
    else:
        webhook = update_webhook(webhook_id, target, name)

    # pprint(webhook)
    sys.stderr.write("New WebHook Target URL: " + webhook["targetUrl"] + "\n")

    return webhook_id

#### Room Utilities
def current_rooms():
    spark_u = spark_host + "v1/rooms"
    page = requests.get(spark_u, headers = spark_headers)
    rooms = page.json()
    return rooms["items"]

def leave_room(room_id):
    # Get Membership ID for Room
    membership_id = get_membership_for_room(room_id)
    spark_u = spark_host + "v1/memberships/" + membership_id
    page = requests.delete(spark_u, headers = spark_headers)

def get_membership_for_room(room_id):
    spark_u = spark_host + "v1/memberships?roomId=%s" % (room_id)
    page = requests.get(spark_u, headers = spark_headers)
    memberships = page.json()["items"]

    return memberships

# Standard Utility

def valid_request_check(request):
    try:
        if request.headers["key"] == secret_key:
            return (True, "")
        else:
            error = {"Error": "Invalid Key Provided."}
            sys.stderr.write(error + "\n")
            status = 401
            resp = Response(json.dumps(error), content_type='application/json', status=status)
            return (False, resp)
    except KeyError:
        error = {"Error": "Method requires authorization key."}
        sys.stderr.write(error + "\n")
        status = 400
        resp = Response(json.dumps(error), content_type='application/json', status=status)
        return (False, resp)



if __name__ == '__main__':
    from argparse import ArgumentParser
    import os, sys
    from pprint import pprint


# Setup and parse command line arguments
#    parser = ArgumentParser("MyHero Spark Interaction Bot")
#    parser.add_argument(
#        "-t", "--token", help="Spark User Bearer Token", required=False
#    )
#    parser.add_argument(
#        "-a", "--app", help="Address of app server", required=False
#    )
#    parser.add_argument(
#        "-k", "--appkey", help="App Server Authentication Key Used in API Calls", required=False
#    )
#    parser.add_argument(
#        "-u", "--boturl", help="Local Host Address for this Bot", required=False
#    )
#    parser.add_argument(
#        "-b", "--botemail", help="Email address of the Bot", required=False
#    )
#    parser.add_argument(
#        "--demoemail", help="Email Address to Add to Demo Room", required=False
#    )
#    parser.add_argument(
#        "-s", "--secret", help="Key Expected in API Calls", required=False
#    )
#
#    args = parser.parse_args()


    # Set application run-time variables
    # Values can come from
    #  1. Command Line
    #  2. OS Environment Variables
    #  3. Raw User Input
    #bot_url = args.boturl
    bot_url = None
    # adding static link
    #bot_url = "http://chetp-spark.app.mantldevnetsandbox.com"
    #bot_url = "http://127.0.0.1:5000"
    if (bot_url == None):
        bot_url = os.getenv("drummer_spark_bot_url")
        if (bot_url == None):
            bot_url = raw_input("What is the Application Address for this Bot? ")
    # print "Bot URL: " + bot_url
    sys.stderr.write("Bot URL: " + bot_url + "\n")

    #bot_email = args.botemail
    bot_email = None
    # adding static email
    #bot_email = "cpuskarz@cisco.com"
    if (bot_email == None):
        bot_email = os.getenv("drummer_spark_bot_email")
        if (bot_email == None):
            bot_email = raw_input("What is the Email Address for this Bot? ")
    # print "Bot Email: " + bot_email
    sys.stderr.write("Bot Email: " + bot_email + "\n")

    #app_server = args.app
    app_server = None
    # adding static app server
    #app_server = "http://chetp-app.app.mantldevnetsandbox.com"
    #app_server = "http://127.0.0.1:5002"
    # print "Arg App: " + str(app_server)
    if (app_server == None):
        app_server = os.getenv("drummer_app_server")
        # print "Env App: " + str(app_server)
        if (app_server == None):
            get_app_server = raw_input("What is the app server address? ")
            # print "Input App: " + str(get_app_server)
            app_server = get_app_server
    # print "App Server: " + app_server
    sys.stderr.write("App Server: " + app_server + "\n")

# Comment out key section
#    app_key = args.appkey
#    # print "Arg App Key: " + str(app_key)
#    if (app_key == None):
#        app_key = os.getenv("myhero_app_key")
#        # print "Env App Key: " + str(app_key)
#        if (app_key == None):
#            get_app_key = raw_input("What is the app server authentication key? ")
#            # print "Input App Key: " + str(get_app_key)
#            app_key = get_app_key
#    # print "App Server Key: " + app_key
#    sys.stderr.write("App Server Key: " + app_key + "\n")

    #spark_token = args.token
    spark_token = None
    # adding static spark token
    #spark_token = os.getenv("TOKEN")
    #print "Spark Token: " + str(spark_token)
    if (spark_token == None):
        spark_token = os.getenv("spark_token")
        # print "Env Spark Token: " + str(spark_token)
        if (spark_token == None):
            get_spark_token = raw_input("What is the Cisco Spark Token? ")
            # print "Input Spark Token: " + str(get_spark_token)
            spark_token = get_spark_token
    # print "Spark Token: " + spark_token
    # sys.stderr.write("Spark Token: " + spark_token + "\n")
    #sys.stderr.write("Spark Token: REDACTED\n")

    #secret_key = args.secret
    secret_key = None
    # adding static bot secret
    #secret_key = "SecureBot"
    if (secret_key == None):
        secret_key = os.getenv("drummer_spark_bot_secret")
        if (secret_key == None):
            get_secret_key = raw_input("What is the Authorization Key to Require? ")
            secret_key = get_secret_key
    sys.stderr.write("Secret Key: " + secret_key + "\n")


    # Set Authorization Details for external requests
    spark_headers["Authorization"] = "Bearer " + spark_token
    #app_headers["key"] = app_key


    # Setup The MyHereo Spark Demo Room
    demo_room_id = setup_demo_room()
    sys.stderr.write("Drummer Demo Room ID: " + demo_room_id + "\n")

    # Setup Web Hook to process demo room messages
    webhook_id = setup_webhook(demo_room_id, bot_url, "Drummer Demo Room Webhook")
    sys.stderr.write("Drummer Demo Web Hook ID: " + webhook_id + "\n")


    # If Demo Email was provided, add to room
    #demo_email = args.demoemail
    demo_email = "cpuskarz@cisco.com"
    if demo_email:
        sys.stderr.write("Adding " + demo_email + " to the demo room.\n")
        add_email_demo_room(demo_email, demo_room_id)

    app.run(debug=True, host='0.0.0.0')
