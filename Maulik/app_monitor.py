###############################################################################
# Load packages
###############################################################################
import datetime
import mimetypes
import os
import requests
import smtplib
from email.message import EmailMessage
from pytz import timezone


###############################################################################
# Constants
###############################################################################
APP_KEYWORDS = ['<title>Ask PDF</title>',
                'var ns = clientside["_dashprivate_chatbot-user-input"] = clientside["_dashprivate_chatbot-user-input"] || {};',
                '<script id="_dash-renderer" type="application/javascript">var renderer = new DashRenderer();</script>',
            ] # The correct content that should show on the opening page
APP_KEYWORD_NOT_AUTHORIZED = 'Unauthorized - Domino' # Incorrect content
APP_KEYWORD_NOT_FOUND = 'Not Found - Domino' # Incorrect content
APP_KEYWORD_NOT_FOUND_404 = '404 Not Found' # Incorrect content
APP_KEYWORD_NOT_PUBLISHED = 'App not published - Domino' # Incorrect content
DOMINO_API_HOST = os.environ['DOMINO_API_HOST']
DOMINO_PROJECT_NAME = os.environ.get('DOMINO_PROJECT_NAME')
DOMINO_PROJECT_OWNER = os.environ.get('DOMINO_PROJECT_OWNER')
EMAIL_DOMAIN = 'newyorklife'
EMAIL_RECIPIENTS = ['tianzi_feng@newyorklife.com']
EMAIL_SENDER = 'tianzi_feng@newyorklife.com'
EMAIL_SUBJECT_LINE = 'App Monitoring: Ask PDF QA ({})'.format(datetime.datetime.now(timezone('US/Eastern')))
STATIC_INTERNAL_APP_URL = DOMINO_API_HOST + '/u/' + DOMINO_PROJECT_OWNER + '/' + DOMINO_PROJECT_NAME + '/app'


###############################################################################
# Check the content on the opening page
###############################################################################
def check_app_opening_page_content():
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning) # Disable insecure request warning
    r = requests.get(STATIC_INTERNAL_APP_URL, verify = False)
    email_content = []
    is_running = 1
    if any(app_keyword not in r.text for app_keyword in APP_KEYWORDS): # If any correct content is missing
        is_running = 0
        print('App is not running properly!')
        email_content.append('App is not running properly!')
        if APP_KEYWORD_NOT_AUTHORIZED in r.text:
            print('App is unauthorized')
            email_content.append('App is unauthorized')
        if APP_KEYWORD_NOT_FOUND in r.text:
            print('App is not found')
            email_content.append('App is not found')
        if APP_KEYWORD_NOT_FOUND_404 in r.text:
            print('App is not found (404)')
            email_content.append('App is not found (404)')
        if APP_KEYWORD_NOT_PUBLISHED in r.text:
            print('App is not published')
            email_content.append('App is not published')
        print('=======================================================')
        email_content.append('=======================================================')
        print(r.text) # The content on the incorrect page
        email_content.append(r.text)
    else: # If all correct content is shown
        print('App is running properly')
        email_content.append('App is running properly')
    email_content = '\n'.join(email_content)
    return email_content, is_running


###############################################################################
# Send out emails to notify ourselves
###############################################################################
def send_email(subject, sender, recipients, content = None, directory = None, domain = None):
    mailserver = smtplib.SMTP('mailsmtp.{0}.com'.format(domain))
    if not domain:
        mailserver = smtplib.SMTP('smtp.office365.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.login('email_address@domain.com', 'pwd')

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)

    if content:
        msg.set_content(content)
    
    if directory: # check if attachments exist
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if not os.path.isfile(path):
                continue

            ctype, encoding = mimetypes.guess_type(path)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            msg.add_attachment(open(path, 'rb').read(), maintype = maintype, subtype = subtype, filename = filename)

    mailserver.send_message(msg)
    mailserver.quit()


if __name__ == '__main__':
    email_content, is_running = check_app_opening_page_content()
    if not is_running:
        send_email(EMAIL_SUBJECT_LINE, EMAIL_SENDER, EMAIL_RECIPIENTS, content = email_content, domain = EMAIL_DOMAIN)