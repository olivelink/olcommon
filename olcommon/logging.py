from json_log_formatter import VerboseJSONFormatter

import logging.handlers


class ActorLoggerAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        extra = {
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

class FormatterSetDefaults(logging.Formatter):

    def format(self, record):
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
