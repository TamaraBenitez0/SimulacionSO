
#!/usr/bin/env python
from hardware import *
import log
## from state import State
from readyQueue import *




class ReadyQueue() :

    def __init__(self):
        self.readyQueue = []

    def add(self,pcb):
        self.readyQueue.append(pcb)

    def isEmpty(self):
        return len(self.readyQueue) == 0

    def nextPCB(self):
        return self.readyQueue.pop(0)
