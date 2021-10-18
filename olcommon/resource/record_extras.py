from ctq import acquire
from ctq import resource_path_names

import ctq_sqlalchemy

class RecordExtras(ctq_sqlalchemy.RecordExtras):
    """Add extra helpers to a record class from SQLAlchemy to work
    well with the resource tree.
    """

    @property
    def registry(self):
        """SQLAlchemy defins a regitry which we don't use
        """
        return acquire(self.__parent__).registry

    def __str__(self):
        names = resource_path_names(self)
        path = '/'.join(names)
        return f"<{self.__class__.__name__} {path}>"
