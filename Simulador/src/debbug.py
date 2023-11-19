import pyserial

class Debbug:
    def __init__(self, port, speed):
        self.port = port
        self.speed = speed

    def checkPort(self):
        portas_ativas = []
        for i in range(10):
            try:
                check = serial.Serial(i)
                portas_ativas.append((i, check.portstr))
                check.close()
            except serial.SerialException:
                pass
        return portas_ativas
 
    def writePort(self, value):
        try:
            Obj_porta = serial.Serial(self.port, self.speed)
            Obj_porta.write(value)
            Obj_porta.close()
        except serial.SerialException:
            print("ERROR")
        return valor
 
    def readPort(self):
        try:
            Obj_porta = serial.Serial(porta, baud_rate)
            valor = Obj_porta.read()
            Obj_porta.close()
            return valor
        except serial.SerialException:
            print("ERROR")