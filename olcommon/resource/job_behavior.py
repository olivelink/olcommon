from ctq import resource_path_names
from inspect import ismethod
from olcommon.jobs import resource_call
from olcommon.jobs import resource_emit

import logging


class JobBehavior:

    _job_enqueue_pending = None
    _job_enqueue_in_pending = None
    _job_enqueue_call_pending = None
    _job_enqueue_emit_pending = None

    def enqueue(
        self,
        queue,
        func,
        *args,
        **kwargs,
    ):
        func, args, kwargs = ensure_function(func, args, kwargs)
        item = (queue, func, args, kwargs)
        if self._job_enqueue_pending is None:
            self._job_enqueue_pending = [item]
        else:
            self._job_enqueue_pending.append(item)
   
    def enqueue_call(
        self,
        queue,
        func,
        args=None,
        kwargs=None,
        *enqueue_call_args,
        **enqueue_call_kwargs
    ):
        func, args, kwargs = ensure_function(func, args, kwargs)
        item = (queue, func, args, kwargs, enqueue_call_args, enqueue_call_kwargs)
        if self._job_enqueue_call_pending is None:
            self._job_enqueue_call_pending = [item]
        else:
            self._job_enqueue_call_pending.append(item)

    def enqueue_in(
        self,
        queue,
        time_delta,
        func,
        *args,
        **kwargs,
    ):
        func, args, kwargs = ensure_function(func, args, kwargs)
        item = (queue, time_delta, func, args, kwargs)
        if self._job_enqueue_in_pending is None:
            self._job_enqueue_in_pending = [item]
        else:
            self._job_enqueue_in_pending.append(item)
    
    def enqueue_emit(
        self,
        queue,
        target,
        event_name,
        data=None,
    ):
        target_path = resource_path_names(target)
        item = (queue, target_path, event_name, data)
        if self._job_enqueue_emit_pending is None:
            self._job_enqueue_emit_pending = [item]
        else:
            self._job_enqueue_emit_pending.append(item)

    def on_after_commit(self, success):
        logger = self.get_logger()

        if success:
            # Process enqueue
            if self._job_enqueue_pending:
                for item in self._job_enqueue_pending:
                    logger.debug(f"Enquing: {item}")
                    (queue, func, args, kwargs) = item
                    queue.enqueue(func, *args, **kwargs)

            # Process enqueue_call
            if self._job_enqueue_call_pending:
                for item in self._job_enqueue_call_pending:
                    logger.debug(f"Enquing call: {item}")
                    (queue, func, args, kwargs, enqueue_call_args, enqueue_call_kwargs) = item
                    queue.enqueue_call(func, args, kwargs, *enqueue_call_args, **enqueue_call_kwargs)

            # Process enqueu_in
            if self._job_enqueue_in_pending:
                for item in self._job_enqueue_in_pending:
                    logger.debug(f"Enquing in: {item}")
                    (queue, time_delta, func, args, kwargs) = item
                    queue.enqueue_in(time_delta, func, *args, **kwargs)
            
            if self._job_enqueue_emit_pending:
                for item in self._job_enqueue_emit_pending:
                    logger.debug(f"Enquing emit: {item}")
                    (queue, target_path, event_name, data) = item
                    queue.enqueue(resource_emit, target_path, event_name, data)

        self._job_enqueue_pending = None
        self._job_enqueue_call_pending = None
        self._job_enqueue_in_pending = None

        super().on_after_commit(success)


def ensure_function(func, args, kwargs):
    if ismethod(func):
        # If f is a method, then wrap it in the
        # resource tree method call
        method_name = func.__name__
        resource = func.__self__
        resource_path = resource_path_names(resource)
        func = resource_call
        args = (resource_path, method_name, *args)
    return (func, args, kwargs)
