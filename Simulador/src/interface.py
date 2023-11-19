from tkinter import *

Window = Tk()

class Interface:
    def __init__(self):
        Window.title("Soccer - Simulator")
        Window.geometry('1920x1080')
        self.file = Button(Window, text="File")

    def run(self):
        self.file.grid(column=0, row=0)
        Window.mainloop()