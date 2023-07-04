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
                    (queue, func, args, kwargs) = item
                    job = queue.enqueue(func, *args, **kwargs)
                    logger.debug(f"Enqueued: {job.func_name} {args} {kwargs}: {job.get_id()} ({queue.name})")

            # Process enqueue_call
            if self._job_enqueue_call_pending:
                for item in self._job_enqueue_call_pending:
                    (queue, func, args, kwargs, enqueue_call_args, enqueue_call_kwargs) = item
                    job = queue.enqueue_call(func, args, kwargs, *enqueue_call_args, **enqueue_call_kwargs)
                    logger.debug(f"Enqueued: {job.func_name} {args} {kwargs}: {job.get_id()} ({queue.name})")

            # Process enqueu_in
            if self._job_enqueue_in_pending:
                for item in self._job_enqueue_in_pending:
                    (queue, time_delta, func, args, kwargs) = item
                    assert not isinstance(queue, str), f"queue must be a queue, not a string: {queue}"
                    job = queue.enqueue_in(time_delta, func, *args, **kwargs)
                    logger.debug(f"Enqueued in {time_delta.total_seconds():.3f}s: {job.func_name} {args} {kwargs}: {job.get_id()} ({queue.name})")
            
            if self._job_enqueue_emit_pending:
                for item in self._job_enqueue_emit_pending:
                    (queue, target_path, event_name, data) = item
                    job = queue.enqueue(resource_emit, target_path, event_name, data)
                    logger.debug(f'Enqueued emit "{event_name}" on {target_path} with {data}: {job.get_id()} ({queue.name})')

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
