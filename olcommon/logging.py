from json_log_formatter import VerboseJSONFormatter
from pyramid.request import Request
import logging.handlers
import os


class ActorLoggerAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        extra = {
            "actor": None,
            "actor_ip": None,
            **self.extra,
            **(kwargs.get("extra") or {}),
        }

        # If we have a request in the extra then override actor and actor_ip
        if request := extra.get("request"):
            extra["actor"] = extra.get("actor") or request.unauthenticated_userid  # One day this can be str(request.identity)
            extra["actor_ip"] = extra.get("actor_ip") or request.client_addr

        extra["actor_formatted"] = f'{extra["actor_ip"] or "-"} {extra["actor"] or "-"}'

        # Construct kwargs and return
        kwargs = {
            **kwargs,
            "extra": extra,
        }
        return msg, kwargs

    def set_actor(self, actor):
        self.extra["actor"] = actor

class GoogleLoggingJSONFormatter(VerboseJSONFormatter):

    def mutate_json_record(self, json_record, stack=None):

        # Make sure we keep track of recursive objects
        if stack is None:
            stack = set([id(json_record)])
        else:
            stack = set([id(json_record)]) | stack

        if len(stack) > 10:
            return 

        rec = {}
        for k, v in json_record.items():

            # Check for a good key
            if not isinstance(k, str):
                continue
            if k.startswith("_"):
                continue
            k = str(k)

            # Parse the value
            if (
                isinstance(v, str)
                or isinstance(v, int)
                or isinstance(v, float)
                or isinstance(v, bool)
                or (v is None)
            ):
                pass
            if isinstance(v, Request):
                v = str(v)  # no decending into the request rebbit hole
            elif len(stack) > 5:
                continue  # too deep to recurse any further
            elif id(v) in stack:
                continue  # ignore value as this would be recurssion
            elif isinstance(v, dict):
                new_valvue = self.mutate_json_record(v, stack)
            elif hasattr(v, "__dict__"):
                v = self.mutate_json_record(v.__dict__, stack)
            else:
                v = str(v)
            
            rec[k] = v
    
        return rec

    def json_record(self, message, extra, record):
        extra['logging.googleapis.com/severity'] = record.levelname
        if actor := getattr(record, "actor", None):
            extra["actor"] = actor
        if actor_ip := getattr(record, "actor_ip", None):
            extra["actorIp"] = actor_ip
        if request_method := getattr(record, "request_method", None):
            extra["requestMethod"] = request_method
        if request_url := getattr(record, "request_url", None):
            extra["requestUrl"] = request_url
        if response_status := getattr(record, "response_status", None):
            extra["responseStatus"] = response_status
        if response_content_length := getattr(record, "response_content_length", None):
            extra["responseContentLength"] = response_content_length
        if user_agent := getattr(record, "user_agent", None):
            extra["userAgent"] = user_agent
        if referer := getattr(record, "referer", None):
            extra["referer"] = referer
        if route_name := getattr(record, "route_name", None):
            extra["routeName"] = route_name
        if view_name := getattr(record, "view_name", None):
            extra["viewName"] = view_name
        if latency := getattr(record, "latency", None):
            extra["latency"] = latency
        return super().json_record(message, extra, record)

def _json_serializable(obj):
    try:
        return {k: v for k, v in obj.__dict__.items() if isinstance(k, str) and not k.startswith("_")}
    except AttributeError:
        return str(obj)

class FormatterSetDefaults(logging.Formatter):

    def format(self, record):
        record.host = os.environ.get("HOSTNAME")
        record.pid = os.getpid()
        if not hasattr(record, "actor_ip"):
            record.actor_ip = None
        if not hasattr(record, "actor"):
            record.actor = None
        if not hasattr(record, "actor_formatted"):
            record.actor_formatted = "- -"
        message = super().format(record)
        return message


class CustomSubjectSMTPHandler(logging.handlers.SMTPHandler):

    def getSubject(self, record):
        subject = self.subject.format(**record.__dict__)
        if record.exc_info is not None:
            subject += f": {record.exc_info[0].__name__}"
        return subject
