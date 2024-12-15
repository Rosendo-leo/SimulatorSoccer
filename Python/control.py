import tkinter as tk
from datetime import timedelta

class Control:
    def __init__(self, root) -> None:
        self.root = root
        self.root.title("Controle")
        root.geometry("400x300")
        icone = tk.PhotoImage(file="Python/logo.png")
        self.root.iconphoto(True, icone)
        self.running = False
        self.start_time = None
        self.elapsed_time = timedelta()

        button = tk.Button(root, text="Iniciar", command=self.start)
        button.pack(pady=20)
        button = tk.Button(root, text="Parar", command=self.stop)
        button.pack(pady=10)

        self.label = tk.Label(root, text="00:00:00", font=("Helvetica", 15))
        self.label.pack(pady=20)

        self.update_clock()

    def update_clock(self) -> None:
        if self.running:
            self.elapsed_time += timedelta(seconds=1)
            self.label.config(text=str(self.elapsed_time).split(".")[0])
        self.root.after(1000, self.update_clock)

    def start(self) -> None:
        if not self.running:
            self.running = True

    def stop(self) -> None:
        self.running = False
        self.elapsed_time = timedelta()
        self.label.config(text="00:00:00")

    def state(self):
        return 0
    
    def stop_running(self):
        return 0