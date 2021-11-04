from ctq import emit


def resource_call(site, path, method_name, *args, **kwargs):
    context = _traverse(site, path)
    func = getattr(context, method_name)
    func(*args, **kwargs)


def resource_emit(site, path, event_name, *args, **kwargs):
    context = _traverse(site, path)
    emit(context, event_name, *args, **kwargs)


def _traverse(root, path):
    context = {"": root}
    if isinstance(path, str):
        path = path.split("/")
    for key in path:
        context = context[key]   
    return context
