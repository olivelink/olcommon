from ctq import resource_path_names
from inspect import ismethod
from olcommon.jobs import resource_call


class JobBehavior:

    _job_enqueue_call_pending = None
    _job_transaction_hooked = False
   
    def enqueue_call(
        self,
        queue,
        func,
        args=None,
        kwargs=None,
        *enqueue_call_args,
        **enqueue_call_kwargs
    ):
        if ismethod(func):
            # If f is a method, then wrap it in the
            # resource tree method call
            method_name = func.__name__
            resource = func.__self__
            resource_path = resource_path_names(resource)
            func = resource_call
            args = (resource_path, method_name, *args)
        self.job_transaction_init()
        self._job_enqueue_call_pending.append(
            (queue, func, args, kwargs, enqueue_call_args, enqueue_call_kwargs),
        )

    def job_transaction_init(self):
        if self._job_enqueue_call_pending is None:
            self._job_enqueue_call_pending = []
        if not self._job_transaction_hooked:
            tx = self.transaction.get()
            tx.addBeforeCommitHook(self.job_transaction_on_after_commit)
            self._job_transaction_hooked = True

    def job_transaction_on_after_commit(self):
        for item in self._job_enqueue_call_pending:
            (queue, func, args, kwargs, enqueue_call_args, enqueue_call_kwargs) = item
            queue.enqueue_call(func, args, kwargs, *enqueue_call_args, **enqueue_call_kwargs)
        self.job_transaction_finish()
    
    def job_transaction_finish(self):
        self._job_enqueue_call_pending = None
        self._job_transaction_hooked = False
