# -*- coding:utf-8 -*-

from repoze.sendmail.mailer import SMTPMailer

import email.mime.multipart
import json
import logging
import requests


logger = logging.getLogger('app')


class SendgridMailer(SMTPMailer):
    """A mailer to send email using a sendgrid template"""

    def __init__(
        self, *args, sendgrid_api_key=None, sendgrid_template_generic=None, **kwargs
    ):
        self.sendgrid_api_key = sendgrid_api_key
        self.sendgrid_template_generic = sendgrid_template_generic
        super().__init__(*args, **kwargs)

    def send(self, fromaddr, toaddrs, message):

        smtpapi_json = message.get('X-SMTPAPI')
        if smtpapi_json:
            smtpapi = json.loads(smtpapi_json, strict=False)
            self.sendgrid_send(smtpapi)
            return

        if not isinstance(message, email.mime.multipart.MIMEMultipart):
            # Non multipart messages to go via SMTP
            return super().send(self, fromaddr, toaddrs, message)

        if message.get_content_subtype() == "report":
            # Send delivery report types (such as mail delivery failure) directy through SMTP
            return super().send(self, fromaddr, toaddrs, message)

        html_part = None
        for part in message.walk():
            if part.get_content_maintype() != "text":
                continue
            if message.get_content_subtype() == "html":
                html_part = part

        if html_part is None:
            return super().send(self, fromaddr, toaddrs, message)

        html = html_part.get_payload(decode=True).decode('utf-8')
        self.send_sendgrid_template(
            fromaddr,
            toaddrs,
            self.sendgrid_template_generic,
            {
                'subject': message['subject'],
                'body': html,
            },
        )

    def send_sendgrid_template(self, fromaddr, toaddrs, template_id, data):
        payload = {
            'from': {
                'email': fromaddr,
            },
            'personalizations': [
                {
                    'to': [{'email': t} for t in toaddrs],
                    'dynamic_template_data': data,
                },
            ],
            'template_id': template_id,
        }
        self.sendgrid_send(payload)

    def sendgrid_send(self, payload):
        logger.debug(f'POST to sendgrid api: {payload}')
        resp = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            json=payload,
            headers={
                'Authorization': f'Bearer {self.sendgrid_api_key}',
                'Content-Type': 'application/json',
            },
        )
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            # Before printing error also print response text
            # This info has usefull debugging information
            logger.error(resp.text)
            raise
