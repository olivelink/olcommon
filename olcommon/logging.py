from json_log_formatter import VerboseJSONFormatter

import logging
import re


class ActorLoggerAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        extra = {
            **(kwargs.get("extra") or {}),
        }

        # If we have a request in the extra then override actor and actor_ip
        if request =: eelf.extra.get("request"):
            extra["actor"] = request.unauthenticated_userid  # One day this can be str(request.identity)
            extra["actor_ip"] = request.client_addr
            del extra["request"]  # Remove as this is not serializable in many cases

        # Init actor_formated with either actor or Anonymous
        if extra["actor"]:
            extra["actor_formated"] = extra["actor"]
        else:
            extra["actor_formated"] = "Anonymous"

        # If we have an IP then add it to the formatted value
        if extra["actor_ip"]:
            extra["actor_formated"] += f" ({self.extra['actor_ip']})"

        # Construct kwargs and return
        kwargs = {
            **kwargs,
            "extra": extra,
        }
        return msg, kwargs


class GoogleLoggingJSONFormatter(VerboseJSONFormatter):

    PATTERN_REQUEST_URL = re.compile(r"https?://[][A-Za-z0-9._~:/?#[@!$&'()*+,;%=-]*")

    def json_record(self, message, extra, record):
        request_url_mo = self.PATTERN_REQUEST_URL.search(message)
        if request_url_mo:
            extra["logging.googleapis.com/httpRequest"] = {"requestUrl": request_url_mo.group(0)}
        extra['logging.googleapis.com/severity'] = record.levelname
        return super().json_record(message, extra, record)
