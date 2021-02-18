from hardware import HARDWARE


class Loader():

    def __init__(self):
        self._baseDir = 0

    def load(self, program):
        progSize = len(program.instructions)
        nuevobd = self.getBaseDir()
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.write(self.getBaseDir(), inst)
            self._baseDir += 1
        return nuevobd

    def getBaseDir(self):
        return self._baseDir
