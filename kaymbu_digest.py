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
import getopt
import sys

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
    links.append(moment_img_tags[0].parent['href'])
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
# returns a tuple of the file content and the Content-disposition header
# the content-disposition header is useful for getting the server-assigned file name for the image
###
def get_photo(link):
  r=requests.get(link)
  if (r.status_code != 200):
    raise ValueError("Unsuccessful requesting photo(s). Code %d returned."%r.status_code)
  return r.content,r.headers['Content-Disposition']

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
  sys.exit(0)
  dryrun=False
  opts,args = getopt.getopt(sys.argv[1:],"d")
  for opt in opts:
    if opt == "-d":
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
        photo,content_disposition=get_photo(link)
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
          filepath="%s-%s"%(filepath,moment) #the file exists, append the moment id to uniquify
        f=open(filepath,'w')
        f.write(photo)
        f.close()
        print "Moment %s saved at %s"%(moment,filepath)
    except ValueError as e:
      print repr(e)
      continue
    print "Pictures for %s saved successfully!"%name
    if (not dryrun):
      result,message=mail.uid('STORE', uid, '+FLAGS', '(\SEEN)')
    if result != "OK":
      print "Problem setting message %s seen"%uid
