from state import *
from abstractInterruptionHandler import AbstractInterruptionHandler
from pcb import Pcb


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        program = irq.parameters
        pid = self.kernel.pcbTable.getNewPID()
        baseDir = self.kernel.loader.load(program)
        pcb = Pcb(PcbState.NEW, baseDir, pid, program.name)
        self.kernel.pcbTable.add(pcb)
        if self.kernel.pcbTable.runningPcb == None:
            pcb.setState(PcbState.RUNNING)
            self.kernel.dispatcher.load(pcb)
            self.kernel.pcbTable.setRunningPcb(pcb)
        else:
            pcb.setState(PcbState.READY)
            self.kernel.readyQueue.add(pcb)
