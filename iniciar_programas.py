import subprocess
import signal
import sys

procesos = []

def cerrar_programas(signum, frame):
    print("Deteniendo programas...")

    for proceso in procesos:
        proceso.terminate()

    for proceso in procesos:
        proceso.wait()

    sys.exit(0)


signal.signal(signal.SIGTERM, cerrar_programas)
signal.signal(signal.SIGINT, cerrar_programas)

python = "/home/rasp4/Documents/Estacion/bin/python"

programas = [
    "adquisicion1.py",
    "programa2.py"
]

for programa in programas:
    proceso = subprocess.Popen([
        python,
        f"/home/rasp4/Documents/{programa}"
    ])
    procesos.append(proceso)

print("Programas iniciados correctamente")

while True:
    for proceso in procesos:
        if proceso.poll() is not None:
            print("Un programa terminó inesperadamente.")
            cerrar_programas(None, None)

    signal.pause()
