#!/usr/bin/env python

##
# Kaymbu digest image downloader.
# Copyright 2018 Matthew F. Coates
# http://github.com/mattjackets
# See LICENSE.txt for license terms.
##

import imaplib
import email
import quopri
import re
from bs4 import BeautifulSoup
import requests
import io
import os
import PIL.Image
import PIL.ExifTags
import argparse
import sys
import hashlib

import config

def get_name_links_date(email_msg):
  email_message = email.message_from_string(email_msg)
  matches=re.search(r'.*\s*([A-Z][a-z]+)\'s Digest from .* for (\d?\d\/\d?\d\/\d\d)',email_message['Subject'])
  name=matches.group(1)
  date=matches.group(2)
 
  html_block=get_first_html_block(email_message)
  decoded_html_block=quopri.decodestring(html_block)
  # Kaymbu emails contain invalid HTML, there is a closing html tag before the body, remove it and add it to the end
  fixed_html=decoded_html_block.replace("</html>","",1)+"</html>\r\n"
  soup=BeautifulSoup(fixed_html,'lxml')
  links=[]
  for moment_img_tag in soup.findAll('img',alt="Download this moment"):
    links.append(moment_img_tag.parent['href'])
  return (name,links,date)

def get_first_html_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_type() == 'text/html':
                return part.get_payload()
    elif email_message_instance.get_content_type() == 'text/html':
        return email_message_instance.get_payload()

###
# link should be a link to the image
# returns the file content
###
def get_photo(link):
  r=requests.get(link)
  if (r.status_code != 200):
    raise ValueError("Unsuccessful requesting photo(s). Code %d returned."%r.status_code)
  return r.content

def get_mail_connection(imap_server,mail_username,mail_password):
  mail = imaplib.IMAP4_SSL(imap_server)
  mail.login(mail_username,mail_password)
  mail.select("inbox")
  return mail

def get_new_digest_message_uids(mail):
  result,search_results=mail.uid('search',None,'(UNSEEN SUBJECT "s Digest from ")')
  message_uids=search_results[0].split()
  return message_uids

def get_exif(img):
  exif = {
    PIL.ExifTags.TAGS[k]: v
    for k, v in img._getexif().items()
    if k in PIL.ExifTags.TAGS
  }
  return exif
  
if __name__=="__main__":
  dryrun=False
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument('--dryrun',action='store_true')
  args = arg_parser.parse_args()
  if (args.dryrun):
    print "DRY RUN - messages will not be marked as read."
    dryrun=True
    
  mail=get_mail_connection(config.imap_server,config.mail_username,config.mail_password)
  message_uids=get_new_digest_message_uids(mail)
  print "%d new kaymbu digest messages"%len(message_uids)

  for uid in message_uids:
    print "Starting work on message %s"%uid
    #result,msg_data=mail.uid('fetch',uid,'(RFC822)')
    result,msg_data=mail.uid('fetch',uid,'(BODY.PEEK[])')
    if result != "OK":
      print "Problem fetching message %s"%uid
      continue
    #result,message=mail.uid('STORE', uid, '-FLAGS', '(\SEEN)')
    #if result != "OK":
    #  print "Problem setting message %s unseen"%uid
    anemail=msg_data[0][1]
    name,links,date=get_name_links_date(anemail)
    print "%s's photos from %s"%(name,date)
    
    path=os.path.join(config.output_path,name)
    try:
      os.mkdir(path)
    except OSError:
      pass
    try:
      serial=0
      for link in links:
        photo=get_photo(link)
        image=PIL.Image.open(io.BytesIO(photo))
        exif_data=get_exif(image)
        try:
          photo_taken_at=exif_data['DateTime'].replace(':','-')
        except KeyError:
          # the date/time exif data is missing, use the date from the email subject + serial number
          serial+=1
          sdate=[int(x) for x in date.split('/')]
          photo_taken_at="20%02d-%02d-%02d-%03d"%(sdate[2],sdate[0],sdate[1],serial)
        filepath=os.path.join(path,photo_taken_at+".jpg")
        if (os.path.isfile(filepath)):
          photo_hash = hashlib.sha1(photo).hexdigest()
          #the file exists, append the sha1 hash to uniquify
          filepath=os.path.join(path,photo_taken_at+"-"+photo_hash+".jpg")
        f=open(filepath,'w')
        f.write(photo)
        f.close()
        print "Moment saved at %s"%filepath
    except ValueError as e:
      print repr(e)
      continue
    print "Pictures for %s saved successfully!"%name
    if (not dryrun):
      result,message=mail.uid('STORE', uid, '+FLAGS', '(\SEEN)')
    if result != "OK":
      print "Problem setting message %s seen"%uid
