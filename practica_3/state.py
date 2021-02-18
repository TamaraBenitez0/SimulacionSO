from enum import Enum


class PcbState(Enum):
    NEW = 'New'
    READY = "Ready"
    RUNNING = "Running"
    WAITING = "Waiting"
    TERMINATED = "Terminated"
