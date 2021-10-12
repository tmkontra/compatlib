import sys
from compatlib import compat


class MyCompatibleClass:
    def __init__(self, data):
        self.data = data

    @compat.after(3, 6)
    def process(self):
        print("running 3.6!")
        return 3.6

    @compat.after(3, 7)
    def process(self):
        print("running 3.7!")
        return 3.7

if __name__ == "__main__":
    ver_info = sys.version_info
    _36 = MyCompatibleClass("ok").process.invoke(ver_info)()
    assert _36 == 3.6, _36
    ver_info = (3,7)
    _37 = MyCompatibleClass("ok").process.invoke(ver_info)()
    assert _37 == 3.7, _37

