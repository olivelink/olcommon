from ctq import emit


def site_call(site, method_name, *args, **kwargs):
    func = getattr(site, method_name)
    func(*args, **kwargs)


def resource_call(site, path, method_name, *args, **kwargs):
    context = {"": site}
    if isinstance(path, str):
        path = path.split("/")
    for key in path:
        context = context[key]
    func = getattr(context, method_name)
    func(*args, **kwargs)


def resource_emit(site, path, event_name, *args, **kwargs):
    context = {"": site}
    if isinstance(path, str):
        path = path.split("/")
    for key in path:
        context = context[key]
    emit(context, event_name, *args, **kwargs)
