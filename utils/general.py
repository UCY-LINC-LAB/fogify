import subprocess
from threading import Thread


class AsyncTask(Thread):

    def __init__(self, obj, func, args=[], kwargs={}):

        self.obj = obj
        self.func = func
        self.args = args
        self.kwargs = kwargs
        super(AsyncTask, self).__init__()

    def run(self):
        func = getattr(self.obj.__class__, self.func)
        if len(self.args) > 0 and len(self.kwargs) > 0:
            return func(self.obj, *self.args, **self.kwargs)
        if len(self.args) > 0:
            return func(self.obj, *self.args)
        if len(self.kwargs) > 0:
            return func(self.obj, **self.kwargs)

        return func(self.obj)
