from hardware import *
from so import *
import log


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 28 "cells"
    HARDWARE.setup(28)

    ## Switch on computer
    HARDWARE.switchOn()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    schedulerExp = SchedulerExpropiativo()
    schedulerNoExp = SchedulerNoExpropiativo()
    schedulerFCFS = SchedulerFCFS()
    # schedulerRoundRobin = SchedulerRoundRobin(quantum=3) ##para evitar que encienda el timer

    kernel = Kernel(schedulerFCFS)  ##debe asignarse un scheduler

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ################## usando frameSize 4
    prg1 = Program([ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(4)]) #pags 3 4*3 = 12
    prg2 = Program([ASM.CPU(7)]) # 2 pags 4*2 =8
    prg3 = Program([ASM.CPU(4), ASM.IO(), ASM.CPU(1)]) #pags 2 4*2=8
    kernel.fileSystem.write('c:/prg1.exe', prg1)
    kernel.fileSystem.write('c:/prg2.exe', prg2)
    kernel.fileSystem.write('c:/prg3.exe', prg3)
    # ejecutamos los programas a partir de un “path” (con una prioridad x)   " \
    kernel.run('c:/prg1.exe', 0)
    kernel.run('c:/prg2.exe', 2)
    kernel.run('c:/prg3.exe', 1)


