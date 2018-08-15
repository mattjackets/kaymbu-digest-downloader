# Kaymbu digest image downloader

A bit of Python that will check an imap server for new Kaymbu digest emails, download all the images from the Kaymbu site, and mark the message read.

## Getting Started

Edit the config.py file with your imap server's & email account information (host name, username, and password)
Set the path where you would like the images saved on your computer.

### Prerequisites

Required Python modules:
* imaplib
* email
* quopri
* re
* BeautifulSoup
* requests
* io
* os
* PIL

## Deployment

I recommend setting up cron to run this weekly, but you can run it however you please.

## Authors

* **Matt Coates** - *Initial work* - [mattjackets](https://github.com/mattjackets)

## License

This project is licensed under the BSD License - see the [LICENSE.txt](LICENSE.txt) file for details


