from json_log_formatter import VerboseJSONFormatter

import logging
import re


class ActorLoggerAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        if self.extra["actor"]:
            actor_formated = self.extra["actor"]
        else:
            actor_formated = "anonymous"
        if self.extra["actor_ip"]:
            actor_formated += f" ({self.extra['actor_ip']})"
        extra = {
            **kwargs.get("extra", {}),
            "actor": self.extra["actor"],
            "actor_ip": self.extra["actor_ip"],
            "actor_formated": actor_formated,
        }
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
