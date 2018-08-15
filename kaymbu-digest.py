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
import zipfile
import io
import os

import config

def get_name_and_link(email_msg):
  email_message = email.message_from_string(email_msg)
  name=re.search(r'.*\s*([A-Z][a-z]+)\'s Digest from ',email_message['Subject']).group(1)
 
  html_block=get_first_html_block(email_message)
  decoded_html_block=quopri.decodestring(html_block)
  # Kaymbu emails contain invalid HTML, there is a closing html tab before the body, remove it and add it to the end
  fixed_html=decoded_html_block.replace("</html>","",1)+"</html>\r\n"
  soup=BeautifulSoup(fixed_html,'lxml')
  link=soup.find('a',text="Click here to download all images")['href']
  return (name,link)

def get_first_html_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_type() == 'text/html':
                return part.get_payload()
    elif email_message_instance.get_content_type() == 'text/html':
        return email_message_instance.get_payload()

def get_momentIds(url):
  r=requests.get(url)
  if (r.status_code != 200):
    raise ValueError("Unsuccessful requesting moments page. Code %d returned."%r.status_code)
  moments=re.search(r'\window\.momentIds = \[([\",a-f0-9]+)\];',r.text).group(1).replace('"','').split(',')
  return moments

def get_photo_zip(moments):
  r=requests.get("http://export.kaymbu.com/download/moments?%s"%'&'.join(moments))
  if (r.status_code != 200):
    raise ValueError("Unsuccessful requesting zip archive. Code %d returned."%r.status_code)
  return r.content

if __name__=="__main__":
  mail = imaplib.IMAP4_SSL(config.imap_server)
  mail.login(config.mail_username,config.mail_password)
  mail.select("inbox")
  
  result,search_results=mail.uid('search',None,'(UNSEEN SUBJECT "s Digest from ")')
  message_uids=search_results[0].split()
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
    name,link=get_name_and_link(anemail)
    #print name
    #print link
    try:
      momentIds=get_momentIds(link)
      print momentIds
      zipdata=get_photo_zip(momentIds)
    except ValueError as e:
      print repr(e)
      continue
    z=zipfile.ZipFile(io.BytesIO(zipdata))
    print "Extracting files for %s"%name
    z.extractall(os.path.join(config.output_path,name))
    print "Pictures for %s extracted successfully!"%name
    result,message=mail.uid('STORE', uid, '+FLAGS', '(\SEEN)')
    if result != "OK":
      print "Problem setting message %s seen"%uid
