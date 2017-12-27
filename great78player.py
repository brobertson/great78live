#!/usr/bin/env python
import collections,json, os, requests, timeit, tweepy
from tweepy import OAuthHandler, Stream
from tweepy.streaming import StreamListener
import xml.etree.ElementTree as ET
import urllib, urllib2
import pygame
import subprocess
from pygame import mixer
import great78player_config as cfg
mixer.init()
auth = OAuthHandler(cfg.consumer_key, cfg.consumer_secret)
auth.set_access_token(cfg.access_token, cfg.access_secret)
api = tweepy.API(auth)
archive_url_prefix = "https://www.archive.org/download/"
great78_twitter_account_id = '871797802397044738'

#This is a fifo collection of size 100. Here we're just initializing it
url_queue = collections.deque(100*[0],100) 

#this function calls the linux 'mpg123' command to play the mp3 file
#I tried using pygame library, but couldn't get mp3 to work
def play_mp3(path):
        subprocess.Popen(['mpg123', '-q', path]).wait()

def get_extended_url_from_status(tweepy_status):
    my_json = status._json
    expanded_url = my_json["entities"]["urls"][0]["expanded_url"]
    return expanded_url

for status in api.user_timeline(id= great78_twitter_account_id , count=100):
    url_queue.append(get_extended_url_from_status(status))


#class MyListener(StreamListener):
#   def on_data(self, data):
#      try:
            #print data
            #url_queue.appendleft(data)
#            return True
#      except BaseException as e:
#          print("Error on_data: %s" % str(e))
#      return True
#   def on_error(self, status):
#      print(status)
#      return True

#here's one way to do things if you want the stream to be 100% live
#now that they're publishing every hour, this does not play so pleasingly
#twitter_stream = Stream(auth, MyListener())
#twitter_stream.filter(follow=['871797802397044738'], async=True)
# )

for url in url_queue:
    playing_file = ""
    try:
        disc_id = url.split('/')[4]
    except Exception as e:
        print "ERROR: could not find 4 parts split by '/' on url '", url, "'"
        print "skiping to next url in queue"
        print e
        continue
    print "disc_id: ", disc_id
    info_xml_url = archive_url_prefix+disc_id+"/"+disc_id+"_files.xml"
    print "xml_url: ", info_xml_url
    try:
        info_xml = ET.ElementTree(file=urllib2.urlopen(info_xml_url))
    except Exception as e:
        print "ERROR: could not download or parse xml_url."
        print "skipping to next url in queue."
        continue
    for filename in info_xml.findall('file'):
        name = filename.get('name')
        #by convention, archive names all the test mp3 files with '78_'
        #at the beginning of the filename. However, the one that they
        #select for use has a plain-text name, and does not start thus.
        #so we search through for a name that both doesn't start with '78_'
        #and is an mp3 file. (We could use .flac, but that would require
        #about 10x the time and space for downloads).
        if (not name.startswith('78_')) and name.endswith('.mp3'):
            playing_file = name
            break
    #what if we never find a suitable filename in the above loop? 
    #then playing_file will still be empty, and we'll do the following
    if playing_file == "":
        print "ERROR: found no acceptable file to play. Here is the xml dump:"
        print ET.tostring(info_xml, pretty_print=True)
        #now skip this url in queue, because we won't be able to do 
        #anything with it
        break
    else:
        print "playing_file: ", playing_file
    #compose the url for the mp3 we want to play. This simply
    #conforms to the standards of the archive website.

    #There is an issue when the name of the playing_file has a ? in it.
    #I've tried various URL encoding libraries to ditch this, but then the value
    #gets turned back into a ? by the request.
    #the result is that such tunes never get downloaded or played
    mp3_url = archive_url_prefix + disc_id + "/" + playing_file
    print "mp3_url: ",mp3_url
    print "\t downloading ..."
    mp3file='./'+disc_id+'.mp3'
    #now download the url of the mp3 to the mp3file locally
    try:
        import timeit
        tic=timeit.default_timer()
        mp3stream = requests.get(mp3_url)
        print "the encoded url is: ", mp3stream.url
        print "status: ", mp3stream.status_code
        with open(mp3file, 'wb') as output:
            for chunk in mp3stream.iter_content(chunk_size=128):
                output.write(chunk)
        #mp3stream = urllib2.urlopen(mp3_url)
        #with open(mp3file,'wb') as output:
        #    output.write(mp3stream.read())
        toc=timeit.default_timer()
        print "\tthis took ", toc-tic, " seconds."
        #this command blocks until the playing is complete
        tic=timeit.default_timer()
        print "\tplaying ..."
        play_mp3(mp3file)
        print "\tdone playing."
        toc = timeit.default_timer()
        print "\tthis took ", toc-tic, " seconds."
        print
        #delete the file now that we've played it.
        #we might consider different logic, like putting it in a separate 
        #directory for potential reuse
        os.remove(mp3file)
    except Exception as e:
        print e
