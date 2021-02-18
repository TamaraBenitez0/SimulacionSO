import log
from state import *
from abstractInterruptionHandler import AbstractInterruptionHandler
from hardware import HARDWARE


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcbFinalizado = self.kernel.pcbTable.runningPcb
        self.kernel.dispatcher.save(pcbFinalizado)
        pcbFinalizado.setState(PcbState.TERMINATED)
        if not (self.kernel.readyQueue.isEmpty()):
            nextPcb = self.kernel.readyQueue.nextPCB()
            self.kernel.dispatcher.load(nextPcb)
            nextPcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.add(nextPcb)
