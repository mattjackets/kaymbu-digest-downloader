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
  # Kaymbu emails contain invalid HTML, there is a closing html tag before the body, remove it and add it to the end
  fixed_html=decoded_html_block.replace("</html>","",1)+"</html>\r\n"
  soup=BeautifulSoup(fixed_html,'lxml')
  link=None
  link_tag=soup.find('a',text="Click here to download all images")
  if (link_tag): #we have more than one moment/photo in this email
    link=link_tag['href']
  else: #there is only one moment/photo in this email
    moment_img_tags=soup.findAll('img',alt="Download this moment")
    if (len(moment_img_tags) == 1):
      link=moment_img_tags[0].parent['href']
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

###
# moments should be a list of moment ids.
# returns a tuple of the file content and the Content-disposition header
# If more thn one moment id is in the list, content will be a zip archive
# the content-disposition header is useful for getting the server-assigned file name for the image
###
def get_photos(moments):
  r=requests.get("http://export.kaymbu.com/download/moments?%s"%'&'.join(moments))
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
  
if __name__=="__main__":
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
    name,link=get_name_and_link(anemail)
    #print name
    #print link
    
    path=os.path.join(config.output_path,name)
    try:
      os.mkdir(path)
    except OSError:
      pass
    try:
      momentIds=get_momentIds(link)
      print momentIds
    except ValueError as e:
      print repr(e)
      continue
    try:
      for moment in momentIds:
        photo,content_disposition=get_photos([moment])
        filename=re.search(r'filename=(.*)',content_disposition).group(1)
        filepath=os.path.join(path,filename)
        if (os.path.isfile(filepath)):
          filepath="%s-%s"%(filepath,moment) #the file exists, append the moment id to uniquify
        f=open(filepath,'w')
        f.write(photo)
        f.close()
    except ValueError as e:
      print repr(e)
      continue
    print "Pictures for %s saved successfully!"%name
    result,message=mail.uid('STORE', uid, '+FLAGS', '(\SEEN)')
    if result != "OK":
      print "Problem setting message %s seen"%uid
