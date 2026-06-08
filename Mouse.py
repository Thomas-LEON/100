import tkinter as tk
import pyautogui
import threading
import time

class MouseBouncer:
    def __init__(self, root):
        self.root = root
        self.root.title("DVD Mouse")
        self.root.geometry("200x100")
        # Garde la petite fenêtre toujours au premier plan
        self.root.attributes("-topmost", True) 

        self.running = False
        self.thread = None

        # Récupération de la taille de l'écran
        self.screen_width, self.screen_height = pyautogui.size()

        # Vitesse de déplacement (pixels par itération)
        self.dx = 10
        self.dy = 10

        # Interface : Boutons
        self.start_btn = tk.Button(root, text="Start", command=self.start, width=15)
        self.start_btn.pack(pady=10)

        self.stop_btn = tk.Button(root, text="Stop", command=self.stop, state=tk.DISABLED, width=15)
        self.stop_btn.pack()

    def start(self):
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Capture la position actuelle de la souris pour démarrer de là
        self.x, self.y = pyautogui.position()
        
        # Lance le mouvement dans un thread séparé pour ne pas bloquer la fenêtre
        self.thread = threading.Thread(target=self.bounce)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def bounce(self):
        # Désactive la sécurité de PyAutoGUI qui coupe le script si la souris touche un coin
        pyautogui.FAILSAFE = False 
        
        while self.running:
            self.x += self.dx
            self.y += self.dy

            # Logique de rebond façon logo DVD
            if self.x <= 0 or self.x >= self.screen_width:
                self.dx = -self.dx
            if self.y <= 0 or self.y >= self.screen_height:
                self.dy = -self.dy

            # Applique la nouvelle position à la souris
            try:
                pyautogui.moveTo(self.x, self.y)
            except Exception:
                pass 
            
            # Temps de pause pour gérer la vitesse (0.02s donne un mouvement fluide)
            time.sleep(0.02)

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseBouncer(root)
    root.mainloop()
