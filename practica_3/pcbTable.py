class PCBTable():
    def __init__(self):
        self._pcbList = []
        self._pid = 0
        self._running = None

    def add(self, pcb):
        self._pcbList.append(pcb)

    def getNewPID(self):
        self._pid = self._pid + 1
        return self._pid

    def setRunningPcb(self, pcb):
        self._running = pcb

    @property
    def runningPcb(self):
        return self._running
