from ctq import resource_path_names
from inspect import ismethod
from olcommon.jobs import resource_call


class JobBehavior:

    _job_enqueue_pending = None
    _job_transaction_hooked = False
   
    def enqueue(self, queue, f, *args, **kwargs):
        if ismethod(f):
            # If f is a method, then wrap it in the
            # resource tree method call
            method_name = f.__name__
            resource = f.__self__
            resource_path = resource_path_names(resource)
            f = resource_call
            args = (resource_path, method_name, *args)
        self.job_transaction_init()
        self._job_enqueue_pending.append((queue, f, args, kwargs))

    def job_transaction_init(self):
        if self._job_enqueue_pending is None:
            self._job_enqueue_pending = []
        if self._job_transaction_hooked:
            tx = self.transaction.get()
            tx.addAfterCommitHook(self.job_transaction_on_after_commit)
            self._job_transaction_hooked = True

    def job_transaction_on_after_commit(self):
        for queue, f, args, kwargs in self._job_queue_pending:
            queue.enqueue(f, *args, **kwargs)
        self.job_transaction_finish()
    
    def job_transaction_finish(self):
        self._job_enqueue_pending = None
        self._job_transaction_hooked = False
