#Requires access to Full Archive Search
import os
import sys
import argparse
import requests

from collections import Counter
from dotenv import load_dotenv
load_dotenv(verbose=True)  # Throws error if no .env file is found

consumer_key=os.getenv("TWITTER_CONSUMER_KEY")
consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET")
access_token=os.getenv("TWITTER_ACCESS_TOKEN")
access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
bearer_token=os.getenv("TWITTER_BEARER_TOKEN")

# Argparse for CLI options. Run `python3 replies.py -h` to see the list of arguments.
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--tweet_id", required=True, help="ID of the Tweet for which you want to pull replies")
parser.add_argument("-s", "--start_time", help="The oldest UTC timestamp from which the Tweets will be provided. Format: YYYY-MM-DDTHH:mm:ssZ; for example: 2021-12-04T01:30:00Z. If unspecified, will default to returning Tweets from up to 30 days ago.")
parser.add_argument("-e", "--end_time", help="The newest, most recent UTC timestamp to which the Tweets will be provided. Format: YYYY-MM-DDTHH:mm:ssZ; for example: 2021-12-04T01:30:00Z. If unspecified, will default to [now - 30 seconds].")
args = parser.parse_args()

def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FullArchiveSearchPython"
    return r

def get_parameters():
    params = {'query': f'conversation_id:{args.tweet_id}', 'tweet.fields': 'in_reply_to_user_id,author_id,conversation_id,entities', 'max_results': '500'}
    if args.start_time:
        params.update(start_time = args.start_time)
    if args.end_time:
        params.update(end_time = args.end_time)
    
    return(params, args.tweet_id)

def get_replies(parameters):
    search_url = "https://api.twitter.com/2/tweets/search/all"

    response = requests.request("GET", search_url, auth=bearer_oauth, params=parameters)

    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    
    response_payload = response.json() 

    if response_payload["meta"]["result_count"] == 0:
        sys.exit("No replies to analyze")

    return response_payload

def get_author(tweet_id):
    tweet_lookup_url = f"https://api.twitter.com/2/tweets/{tweet_id}"
    parameters = {'tweet.fields': 'author_id', 'expansions':'author_id', 'user.fields':'username'}

    response = requests.request("GET", tweet_lookup_url, auth=bearer_oauth, params=parameters)
    
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    
    response_payload = response.json()
    author_id = response_payload["data"]["author_id"]
    for user in response_payload["includes"]["users"]:
        author_username = user["username"]

    return(author_id, author_username)

def get_usernames(author_id, replies):

    usernames = []
    direct_replies = []
    print("jjj", replies)
    for reply in replies["data"]: 
        # Only include Tweets that are in direct reply to the original Tweet
        if reply["in_reply_to_user_id"] == author_id:
            direct_replies.append(reply)

    for reply in direct_replies:
        for mention in reply["entities"]["mentions"]:
            usernames.append(mention["username"])

    return(usernames)

def count_and_sort(usernames, author_username):

    ordered_usernames = Counter(usernames)
    
    #Remove mentions of original author from results
    ordered_usernames.pop(f"{author_username}")

    return ordered_usernames

if __name__ == '__main__':
    parameters, original_tweet_id = get_parameters()
    replies = get_replies(parameters)
    author_id, author_username = get_author(original_tweet_id)
    usernames = get_usernames(author_id, replies)
    ordered_usernames = count_and_sort(usernames, author_username)
    print(ordered_usernames, len(ordered_usernames))

# Add pagination if more than 500 Tweets are returned 