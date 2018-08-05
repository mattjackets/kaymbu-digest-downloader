import imaplib
import email
import quopri
import re
from bs4 import BeautifulSoup
import config

def get_name_and_link(email_msg):
  email_message = email.message_from_string(email_msg)
  name=re.search(r'\s(.*)\'s Digest from ',email_message['Subject']).group(1)
 
  html_block=get_first_html_block(email_message)
  decoded_html_block=quopri.decodestring(html_block)
  soup=BeautifulSoup(decoded_html_block,'lxml')
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

mail = imaplib.IMAP4_SSL(config.imap_server)
mail.login(config.mail_username,config.mail_password)
mail.select("inbox")

result,search_results=mail.uid('search',None,'(UNSEEN SUBJECT "s Digest from ")')
for uid in search_results[0].split():
  result,msg_data=mail.uid('fetch',uid,'(RFC822)')
  if result != "OK":
    print "Problem fetching message %s"%uid
  result,message=mail.uid('STORE', uid, '-FLAGS', '(\SEEN)')
  if result != "OK":
    print "Problem setting message %s unseen"%uid
  anemail=msg_data[0][1]
  name,link=get_name_and_link(anemail)
  print name
  print link

