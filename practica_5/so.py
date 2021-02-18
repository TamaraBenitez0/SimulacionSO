#!/usr/bin/env python
from enum import Enum
from hardware import *
import log
from tabulate import tabulate


## emulates a compiled program

class Program():

    def __init__(self, instructions):
        self._instructions = self.expand(instructions)

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({instructions})".format(instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            # print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(
            deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)


class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        readyQueue = self.kernel.readyQueue
        program = irq.parameters
        pid = self.kernel.pcbTable.getNewPID()
        baseDir = self.kernel.loader.load(program[0])
        pcb = Pcb(PcbState.NEW, baseDir, pid, program[0], program[1])
        self.kernel.pcbTable.add(pcb)
        pcbCorriendo = self.kernel.pcbTable.runningPcb
        pageTPcb = self.kernel.memoryManager.pageTableOf(pcb.getPath())
        if pcbCorriendo == None:
            pcb.setState(PcbState.RUNNING)
            self.kernel.dispatcher.load(pcb,pageTPcb)
            self.kernel.pcbTable.setRunningPcb(pcb)

        elif self.kernel.scheduler.mustExpropiate(pcbCorriendo, pcb):
            self.kernel.dispatcher.save(pcbCorriendo)
            pcbCorriendo.setState(PcbState.READY)
            self.kernel.scheduler.agregarAReadyQueue(readyQueue, pcbCorriendo)
            self.kernel.dispatcher.load(pcb, pageTPcb)
            pcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPcb(pcb)
        else:
            pcb.setState(PcbState.READY)
            self.kernel.scheduler.agregarAReadyQueue(readyQueue, pcb)


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.pcbTable.runningPcb
        self.kernel.dispatcher.save(pcb)
        pcb.setState(PcbState.WAITING)
        self.kernel.ioDeviceController.runOperation(pcb, operation[0])
        log.logger.info(self.kernel.ioDeviceController)
        if not (self.kernel.readyQueue.isEmpty()):
            nextPcb = self.kernel.readyQueue.nextPCB()
            pageTPcb = self.kernel.memoryManager.pageTableOf(nextPcb.getPath())
            self.kernel.dispatcher.load(nextPcb,pageTPcb)
            nextPcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPcb(nextPcb)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        readyQueue = self.kernel.readyQueue
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        log.logger.info(self.kernel.ioDeviceController)
        pcbCorriendo = self.kernel.pcbTable.runningPcb
        pageTPcb = self.kernel.memoryManager.pageTableOf(pcb.getPath())
        if pcbCorriendo == None:
            self.kernel.dispatcher.load(pcb)
            pcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPCB(pcb)
        elif self.kernel.scheduler.mustExpropiate(pcbCorriendo, pcb):

            self.kernel.dispatcher.save(pcbCorriendo)
            pcbCorriendo.setState(PcbState.READY)
            self.kernel.scheduler.agregarAReadyQueue(readyQueue, pcbCorriendo)
            self.kernel.dispatcher.load(pcb,pageTPcb)
            pcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPcb(pcb)

        else:
            pcb.setState(PcbState.READY)
            self.kernel.scheduler.agregarAReadyQueue(readyQueue, pcb)


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcbFinalizado = self.kernel.pcbTable.runningPcb
        self.kernel.dispatcher.save(pcbFinalizado)
        pcbFinalizado.setState(PcbState.TERMINATED)
        if not (self.kernel.readyQueue.isEmpty()):
            nextPcb = self.kernel.readyQueue.nextPCB()
            pageTPcb = self.kernel.memoryManager.pageTableOf(nextPcb.getPath())
            self.kernel.dispatcher.load(nextPcb,pageTPcb)
            nextPcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPcb(nextPcb)
            self.kernel.pcbTable.add(nextPcb)


class TimeOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        readyQueue = self.kernel.readyQueue
        if not (self.kernel.readyQueue.isEmpty()):
            pcbCorriendo = self.kernel.pcbTable.runningPcb
            self.kernel.dispatcher.save(pcbCorriendo)
            pcbCorriendo.setState(PcbState.READY)
            self.kernel.scheduler.agregarAReadyQueue(readyQueue, pcbCorriendo)
            nextPcb = self.kernel.readyQueue.nextPCB()
            pageTPcb = self.kernel.memoryManager.pageTableOf(nextPcb.getPath())
            self.kernel.dispatcher.load(nextPcb,pageTPcb)
            nextPcb.setState(PcbState.RUNNING)
            self.kernel.pcbTable.setRunningPcb(nextPcb)
        else:
            HARDWARE.timer.reset()


class StatsInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        self.kernel._gant.tick(HARDWARE.clock.currentTick)


##################################################################
class Pcb:
    def __init__(self, estado, baseDir, pid, prgname, priority):
        self._state = estado
        self._basedir = baseDir
        self._prgname = prgname
        self._pid = pid
        self._pc = 0
        self._priority = priority

    def setState(self, estado):
        self._state = estado

    def getPc(self):
        return self._pc

    def getBaseDir(self):
        return self._basedir

    def setPc(self, pc):
        self._pc = pc

    def getState(self):
        return self._state

    def prioridad(self):
        return self._priority

    def getPath(self):
        return self._prgname


class PCBTable:
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


###############################################################
class Loader:

    def __init__(self, memoryManager, fileSystem):
        self._baseDir = 0
        self._memoryManager = memoryManager
        self._fileSystem = fileSystem

    def load(self, path):
        program = self._fileSystem.read(path)
        instructions=program.instructions
        pageTable = self._memoryManager.createPageTable(path,len (instructions))
        for page in pageTable:
            self.cargarPagina(page, instructions)

    # cargamos la pagina
    def cargarPagina(self, page, instructions):
        frameSize = self._memoryManager.frameSize
        baseDir = page.frame * frameSize
        start = page.page * frameSize
        end = start + frameSize

        if end > len(instructions):
            end = len(instructions)

        for i in range(start, end):
            inst = instructions[i]
            HARDWARE.memory.write(baseDir, inst)
            baseDir += 1


def getBaseDir(self):
    return self._baseDir


class Dispatcher():
    def load(self, pcb, pageTablePcb):
        HARDWARE.cpu._pc = pcb.getPc()
        HARDWARE.mmu._baseDir = pcb.getBaseDir()
        HARDWARE.timer.reset()
        HARDWARE.mmu.resetTLB()
        for i in pageTablePcb:
            HARDWARE.mmu.setPageFrame(i.page, i.frame)

    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu._pc)
        HARDWARE.cpu._pc = -1


#############################################################################333333
class ReadyQueue():

    def __init__(self):
        self.readyQueue = []

    def add(self, pcb):
        self.readyQueue.append(pcb)

    def isEmpty(self):
        return len(self.readyQueue) == 0

    def nextPCB(self):
        return self.readyQueue.pop(0)

    def ordenar(self, exp, booleano):
        self.readyQueue.sort(key=exp, reverse=booleano)


#########################################################################
class PcbState(Enum):
    NEW = 'New'
    READY = 'Ready'
    RUNNING = 'Running'
    WAITING = 'Waiting'
    TERMINATED = 'Terminated'


##########################################################################
class AbstractScheduler():

    def mustExpropiate(self, pcbCargado, nuevoPcb):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    def agregarAReadyQueue(self, readyQueue, pcb):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


class SchedulerFCFS(AbstractScheduler):

    def mustExpropiate(self, pcbCargado, nuevoPcb):
        return False

    def agregarAReadyQueue(self, readyQueue, pcb):
        readyQueue.add(pcb)


###########################################################################
class SchedulerNoExpropiativo(AbstractScheduler):

    def mustExpropiate(self, pcbCargado, nuevoPcb):
        return False

    def agregarAReadyQueue(self, readyQueue, pcb):
        readyQueue.add(pcb)
        readyQueue.ordenar(lambda pcb: pcb.prioridad(), False)


###########################################################################
class SchedulerExpropiativo(AbstractScheduler):

    def mustExpropiate(self, pcbCargado, nuevoPcb):
        return pcbCargado.prioridad() > nuevoPcb.prioridad()

    def agregarAReadyQueue(self, readyQueue, pcb):
        readyQueue.add(pcb)
        readyQueue.ordenar(lambda pcb: pcb.prioridad(), False)


###########################################################################
class SchedulerRoundRobin(AbstractScheduler):

    def __init__(self, quantum):
        HARDWARE.timer.quantum = quantum

    def mustExpropiate(self, pcbCargado, nuevoPcb):
        return False

    def agregarAReadyQueue(self, readyQueue, pcb):
        readyQueue.add(pcb)


# emulates the core of an Operative System
class Kernel:

    def __init__(self, scheduler,frameSize=4):
        ## setup interruption handlers

        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)
        HARDWARE.mmu.frameSize = frameSize

        timeOut = TimeOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeOut)
        stats = StatsInterruptionHandler(self)
        HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, stats)
        HARDWARE.cpu.enable_stats = True
        self._gant = GanttChart(self)
        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self.pcbTable = PCBTable()
        self.dispatcher = Dispatcher()
        self.readyQueue = ReadyQueue()
        self.scheduler = scheduler
        self.fileSystem = FileSystem()
        self.memoryManager = MemoryManager(frameSize)
        self.loader = Loader(self.memoryManager, self.fileSystem)

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    ## emulates a "system call" for programs execution
    def run(self, path, priority):
        tupla = (path, priority)
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, tupla)
        HARDWARE.interruptVector.handle(newIRQ)
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first intruction
        HARDWARE.cpu.pc = 0

    def __repr__(self):
        return "Kernel "


class GanttChart():

    def __init__(self, kernel):
        self._kernel = kernel
        self._table = {'': []}

    @property
    def table(self):
        return self._table

    @property
    def kernel(self):
        return self._kernel

    def program_ready(self, pcb, tickNbr):
        """ registra que el programa perteneciente al pcb dado esta en ready
            de no existir ese programa en el registro lo agrega automaticamente """

        pName = pcb._prgname
        fstCol = ''

        if pName not in self.table[fstCol]:
            self.table[fstCol].append(pName)
        if not (self.kernel.pcbTable.runningPcb == pcb):
            self.table[tickNbr].append('*')

    def program_running(self, pcb, tickNbr):
        """ registra que el programa perteneciente al pcb dado esta en running
            de no existir ese programa en el registro lo agrega automaticamente """

        pName = pcb._prgname
        fstCol = ''

        if not pName in self.table[fstCol]:
            self.table[fstCol] = [pName]

        self.table[tickNbr].append(pcb._pid)

    def program_terminated(self, tickNbr):  # registra que el programa perteneciente al pcb dado esta en ready

        self.table[tickNbr].append('-')

    @property
    def all_PCBs(self):  # denota todos los PCBs de la tabla
        return self.kernel.pcbTable._pcbList

    def tick(self, tickNbr):
        tic = 'tick {}'.format(tickNbr)
        self.table[tic] = []

        for pcb in self.all_PCBs:
            if pcb.getState() == PcbState.TERMINATED:
                self.program_terminated(tic)
            elif pcb.getState() == PcbState.RUNNING:
                self.program_running(pcb, tic)

            elif pcb.getState() == PcbState.READY:
                self.program_ready(pcb, tic)

    @property
    def printable(self):
        return tabulate(self.table, headers="keys")


class FileSystem():
    def __init__(self):  # asocia paths con programas
        self._disk = {}

    def write(self, path, program):
        self._disk[path] = program

    def read(self, path):
        return self._disk[path]


class MemoryManager:

    def __init__(self, size):
        self._frameSize = size
        self._freeFrames = self.getFreeFrames()
        self._usedFrames = []
        self._pageTable = []

    @property
    def frameSize(self):
        return self._frameSize

    def getFreeFrames(self):  # Marcos libres
        frames = []
        size = int(HARDWARE.memory.size / HARDWARE.mmu.frameSize)
        for f in range(0, size):
            frames.append(f)
        return frames

    def allocFrame(self):
        frame = self._freeFrames.pop(0)
        self._usedFrames.append(frame)
        return frame

    def createPageTable(self, path, cantInst):
        cantPags = self.cantidadDePaginas(cantInst)
        for p in range(cantPags):
            self._pageTable.append(PageTableItem(path, p, self.allocFrame()))
        return self.pageTableOf(path)

    def cantidadDePaginas(self, cantInstrucciones):
        if (cantInstrucciones % self._frameSize) > 0:
            return (cantInstrucciones // self._frameSize) + 1
        else:
            return cantInstrucciones // self._frameSize

 ## dado un path reyotna su page table
    def pageTableOf(self, path):
        ret = []
        for item in self._pageTable:
            if item.path == path:
                ret.append(item)
        return ret

## representa un elemento en la page table
class PageTableItem:
    def __init__(self, path, page, frame):
        self._path = path
        self._page = page
        self._frame = frame

    @property
    def path(self):
        return self._path

    @property
    def page(self):
        return self._page

    @property
    def frame(self):
        return self._frame
