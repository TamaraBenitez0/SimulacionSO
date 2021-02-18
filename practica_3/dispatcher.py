from hardware import HARDWARE


class Dispatcher():
    def load(self, pcb):
        HARDWARE.cpu._pc = pcb.getPc()
        HARDWARE.mmu._baseDir = pcb.getBaseDir()

    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu._pc)
        HARDWARE.cpu._pc = -1
