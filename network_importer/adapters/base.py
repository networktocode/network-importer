
from dsync import DSync

class BaseAdapter(DSync):

    def __init__(self, nornir):
        super().__init__()
        self.nornir = nornir

    def init(self):
        raise NotImplementedError
