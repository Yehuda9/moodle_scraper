import csv
import os
import re
import smtplib
import time
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import logging
from os.path import basename
from pathlib import Path

import gspread

Admin_Email = 'Admin_Email@gmail.com'


def notify_users(course_name, topic):
    update_local_emails()
    try:
        topic = topic.replace(':', '\n')
    except:
        pass
    logging.info('notify_users')
    with open('emails.txt', 'r') as f:
        for line in f:
            record = line.split(',', 1)
            if len(record[0]) > 1 and record[1].__contains__(course_name):
                logging.info(f'send email to: {record[0]}')
                logging.info(topic)
                send_email(course_name, topic, record[0])


def update_local_emails():
    sheets_client = gspread.service_account(filename='path to private key')
    try:
        last_update = sheets_client.open('emails').lastUpdateTime
    except Exception:
        logging.exception('google sheet is busy, wait 90 sec')
        time.sleep(90)
        last_update = sheets_client.open('emails').lastUpdateTime
    last_update = last_update.rsplit('.')[0]
    emails_file_path = Path(os.path.join(os.getcwd(), 'emails.txt'))
    if not emails_file_path.is_file() or (emails_file_path.is_file() and time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(
            os.path.getmtime(emails_file_path))) < last_update):
        with open('emails.txt', 'w') as f:
            logging.info('update emails file')
            sheet = sheets_client.open('emails')
            emails = sheet.values_get('responses!B:C').get('values')
            write = csv.writer(f)
            write.writerows(emails)


def is_changed(course_name, course_file_path, topics):
    changed = False
    with open(course_file_path, 'r') as f:
        old_elements = list()
        for line in f:
            old_elements.append(line.rstrip('\n'))
    for topic in topics:
        if topic not in old_elements:
            logging.info(f'new topic: {topic}')
            changed = True
            notify_users(course_name, topic)
    if changed:
        with open(course_file_path, 'w') as f:
            logging.info('update course file')
            for topic in topics:
                f.write(topic + '\n')


def new_course(course_file_path, topics):
    with open(course_file_path, 'w') as f:
        logging.info('save course to file')
        for topic in topics:
            f.write(topic + '\n')


def is_connected(host='https://google.com'):
    try:
        urllib.request.urlopen(host, timeout=15)
        logging.info('internet connection available')
        return True
    except:
        logging.info('internet connection not available')
        return False


def is_valid_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if re.fullmatch(regex, email):
        return True
    else:
        return False


def send_email(subject, text, destination, file_path=None):
    if not is_valid_email(destination):
        return
    sender = 'sender@gmail.com'
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = destination
    msg.attach(MIMEText(text))
    if file_path is not None and file_path.is_file():
        with open(file_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=basename(file_path))
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(file_path)
        msg.attach(part)
    conn = smtplib.SMTP('smtp.gmail.com', 587)
    conn.connect('smtp.gmail.com', 587)
    conn.ehlo()
    conn.starttls()
    conn.ehlo()
    conn.set_debuglevel(False)
    conn.login('username', 'password')
    try:
        conn.sendmail(sender, destination, msg.as_string())
    finally:
        conn.quit()


def try_driver(callback, tries=3):
    try:
        logging.info('try callback')
        callback()
        return
    except Exception:
        logging.exception('callback failed')
        c = 0
        while not is_connected() and c < tries:
            logging.info('not connected now, try again in 5 sec')
            c += 1
            time.sleep(5)
    try:
        logging.info('connected to internet or run out of tries, try callback for the last time')
        callback()
    except Exception as e:
        logging.info('connection failed')
        raise e
