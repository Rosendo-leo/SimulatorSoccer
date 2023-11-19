from tkinter import *

Window = Tk()

Window.title("Soccer - Simulator")
Window.geometry('1920x1080')
fileB = Button(Window, text="File", command=fileClick)
runB = Button(Window, text="Run")
editB = Button(Window, text="Edit")
exitB = Button(Window, text="Exit", command=Window.quit)

def run():
  fileB.grid(column=0, row=0)
  runB.grid(column=1, row=0)
  editB.grid(column=2, row=0)
  exitB.grid(column=3, row=0)
  Window.mainloop()

def fileClick():
  print("SIM")