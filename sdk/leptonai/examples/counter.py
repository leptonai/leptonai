from leptonai.photon.runner import RunnerPhoton as Runner, handler


class Counter(Runner):
    def init(self):
        self.counter = 0

    @handler("add")
    def add(self, x: int) -> int:
        self.counter += x
        return self.counter

    @handler("sub")
    def sub(self, x: int) -> int:
        self.counter -= x
        return self.counter
