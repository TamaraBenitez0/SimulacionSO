import state


class Pcb:
    def __init__(self, estado, baseDir, pid, prgname):
        self._state = state
        self._basedir = baseDir
        self._prgname = prgname
        self._pid = pid
        self._pc = 0

    def setState(self, estado):
        self._state = estado

    def getPc(self):
        return self._pc

    def getBaseDir(self):
        return self._basedir

    def setPc(self, pc):
        self._pc = pc
