import log
from state import *
from abstractInterruptionHandler import AbstractInterruptionHandler


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        log.logger.info(self.kernel.ioDeviceController)
        if self.kernel.pcbTable.runningPcb == None:
            self.kernel.dispatcher.load(pcb)
            pcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPCB(pcb)
        else:
            pcb._state=PcbState.READY
            self.kernel.readyQueue.add(pcb)
