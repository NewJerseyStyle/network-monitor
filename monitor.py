import time
import psutil
import pickle
import os.path
import sendgrid
from sendgrid.helpers.mail import *

import configparser
config = configparser.ConfigParser()
config.optionxform = str  #reference: http://docs.python.org/library/configparser.html
config.read('netio-mon.conf')

NETWORK_INTERFACE = config.get('Network', 'INTERFACE')
NETWORK_LIMIT = int(config.get('Network', 'LIMIT'))
NETWORK_MAX = int(config.get('Network', 'MAX'))
SENDGRID_API_KEY = config.get('Email', 'SENDGRID_API_KEY')
TIME_INTERVAL = config.get('Misc', 'TIME_INTER')

import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M',
                    handlers=[logging.FileHandler('my.log', 'w', 'utf-8'), ])


def create_message(sender, to, subject, message_text):
    logging.info("send email::" + message_text)
    from_email = Email(sender)
    to_email = To(to)
    subject = subject
    content = Content("text/plain", message_text)
    return Mail(from_email, to_email, subject, content)


def send_message(service, message):
    return service.client.mail.send.post(request_body=message.get())


def update_snapshot():
    netio = psutil.net_io_counters(pernic=True)
    last_snapshot = netio[NETWORK_INTERFACE].bytes_sent + netio[NETWORK_INTERFACE].bytes_recv
    with open('netio.pkl', 'wb') as f:
        pickle.dump(last_snapshot, f)
    logging.info("IO (up&down) on %s total %s bytes used" %(NETWORK_INTERFACE, last_snapshot))


if not os.path.exists('netio.pkl'):
    update_snapshot()
else:
    with open('netio.pkl', 'rb') as f:
        last_snapshot = pickle.load(f)

service = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

have_sent = False
while True:
    time.sleep(TIME_INTERVAL)
    netio = psutil.net_io_counters(pernic=True)
    net_usage = netio[NETWORK_INTERFACE].bytes_sent + netio[NETWORK_INTERFACE].bytes_recv - last_snapshot
    if net_usage > NETWORK_LIMIT and not have_sent:
    	gb = net_usage / 2**30
        message = create_message(
            config.get('Email', 'from'),
            config.get('Email', 'to'),
            config.get('Email', 'subject'),
            'The network have used %s bytes (~%.2f GB)' %(net_usage, gb))
        send_message(service, message)
        have_sent = True
    elif net_usage >= NETWORK_MAX:
        update_snapshot()
        have_sent = False
