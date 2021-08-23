from ctq import acquire
from decimal import Decimal
from uuid import UUID

import json
import pyramid_mailer.message


class SendGridBehavior:

    def sendgrid_send_multi(
        self,
        personalizations,
        noreply=False,
        from_name=None,
        from_addr=None,
        reply_to_name=None,
        reply_to_addr=None,
        template_id=None,
    ):
        """Sends an email to a one or more recipients.

        Args:

            personalizations (List[Dict]): recipient and template data. structured like;
                [
                    {
                        "to": [{"email": "jeremy@olivelink.net", "name": "Test Name"}],
                        "dynamic_template_data": { "name": "Test Name", "abk_name": "aaaa" }
                    }
                ]
            noreply (bool): Weather the email is to be a no-reply email. Use the system noreply settings
            from_name (str): The from name of the email. If None use from settings
            from_addr (str): The from email address. If None use from settings
            reply_to_name (str): The email name to use as the reply-to recipient
            reply_to_addr (str): The email address to use as the reply-to address
            template_id (str): The template to use for the email. This can be either the template
                id in sendgrid or a value in the settings of the form sendgrid_template_{template_id}
        """
        payload = {}

        # Sender information
        registry = acquire(self).registry
        from_name = from_name or registry['site_email_from_name']
        if from_addr is None:
            if noreply:
                from_addr = registry['site_noreply_email']
            else:
                from_addr = registry['site_email']
        payload['from'] = {
            'email': from_addr,
            'name': from_name,
        }

        # Reply to headers
        if reply_to_addr:
            payload['reply_to'] = {'email': reply_to_addr}
            if reply_to_name:
                payload['reply_to']['name'] = reply_to_name

        # Is template id a known template in the settings
        template_id = template_id or 'generic'
        template_id = registry.get(f'sendgrid_template_{template_id}', template_id)

        # Add template data
        if template_id:
            payload['template_id'] = template_id

        # JSON encoder to convert decimals to strings (since will be used as strings in emails)
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal) or isinstance(o, UUID):
                    return str(o)
                return super().default(o)

        # Send in batches to stay within Sendgrid limits
        batch_size = 1000
        for batch_start in range(0, len(personalizations), batch_size):

            # Get the items for the batch
            batch_items = personalizations[batch_start : batch_start + batch_size]

            # Encode the data into the X-SMTPAPI header of a message
            payload_json = json.dumps(
                {'personalizations': batch_items, **payload},
                cls=CustomJSONEncoder,
            )
            acquire(self).mailer.send(
                pyramid_mailer.message.Message(
                    subject='No subject',
                    recipients=[registry['site_noreply_email']],
                    body='No message',
                    sender=registry['site_noreply_email'],
                    extra_headers={'X-SMTPAPI': payload_json},
                )
            )

    def sendgrid_send_email(
        self,
        to_addr=None,
        to_name=None,
        noreply=False,
        from_name=None,
        from_addr=None,
        reply_to_name=None,
        reply_to_addr=None,
        template_id=None,
        data=None,
        cc_addr=None,
        cc_name=None,
    ):
        """Send an email using the sendgrid templates through the SMTP API

        Args:

            to_addr (str): The recipiant email address
            to_name (str): The recipiant name
            noreply (bool): Weather the email is to be a no-reply email. Use the system noreply settings
            from_name (str): The from name of the email. If None use from settings
            from_addr (str): The from email address. If None use from settings
            reply_to_name (str): The email name to use as the reply-to recipient
            reply_to_addr (str): The email address to use as the reply-to address
            template_id (str): The template to use for the email. This can be either the template
                id in sendgrid or a value in the settings of the form sendgrid_template_{template_id}
            data (dict): A data dictionary to be sent to be used as the variable substitutions in the template
        """

        # Create personalization data
        envelope = {'email': to_addr}
        if to_name:
            envelope['name'] = to_name
        personalization = {'to': [envelope]}
        if data:
            personalization['dynamic_template_data'] = data

        # Support cc
        if cc_addr:
            envelope = {'email': cc_addr}
            if cc_name:
                envelope['name'] = cc_name
            personalization['cc'] = [envelope]

        self.sendgrid_send_multi(
            [personalization],
            noreply,
            from_name,
            from_addr,
            reply_to_name,
            reply_to_addr,
            template_id,
        )
