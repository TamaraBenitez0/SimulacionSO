import log
from state import *
from abstractInterruptionHandler import AbstractInterruptionHandler
from hardware import HARDWARE


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.pcbTable.runningPcb
        self.kernel.dispatcher.save(pcb)
        pcb.setState(PcbState.WAITING)
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        log.logger.info(self.kernel.ioDeviceController)
        if not (self.kernel.readyQueue.isEmpty()):
            nextPcb = self.kernel.readyQueue.nextPCB()
            self.kernel.dispatcher.load(nextPcb)
            nextPcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPcb(nextPcb)
