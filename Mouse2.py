import tkinter as tk
import pyautogui
import threading
import time

class SafeMouseBouncer:
    def __init__(self, root):
        self.root = root
        self.root.title("DVD Mouse (Sécurisé)")
        self.root.geometry("250x120")
        self.root.attributes("-topmost", True) 

        self.running = False
        self.thread = None

        self.screen_width, self.screen_height = pyautogui.size()
        self.dx = 10
        self.dy = 10

        # Position théorique de la souris gérée par le script
        self.x, self.y = 0, 0 

        self.start_btn = tk.Button(root, text="Start", command=self.start, width=20, bg="#d4edda")
        self.start_btn.pack(pady=10)

        self.stop_btn = tk.Button(root, text="Stop", command=self.stop, state=tk.DISABLED, width=20, bg="#f8d7da")
        self.stop_btn.pack()

        self.label = tk.Label(root, text="Bouge la souris pour stopper", fg="gray")
        self.label.pack(pady=5)

    def start(self):
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.x, self.y = pyautogui.position()
        
        self.thread = threading.Thread(target=self.bounce)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def stop_from_thread(self):
        """Permet de réinitialiser l'interface proprement depuis le thread secondaire"""
        self.running = False
        self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def bounce(self):
        # IMPORTANT : Réactivation du Fail-Safe (un coup dans un coin de l'écran = arrêt)
        pyautogui.FAILSAFE = True 
        
        # Petite pause pour laisser le temps à l'utilisateur de lâcher la souris au départ
        time.sleep(0.5) 
        self.x, self.y = pyautogui.position()

        while self.running:
            # 1. VERIFICATION : Est-ce que l'utilisateur a touché à la souris ?
            curr_x, curr_y = pyautogui.position()
            
            # Si l'écart entre la position réelle et la position théorique est > à 10 pixels,
            # cela signifie que l'utilisateur a bougé la souris manuellement.
            if abs(curr_x - self.x) > 10 or abs(curr_y - self.y) > 10:
                self.stop_from_thread()
                break

            # 2. LOGIQUE DE REBOND
            self.x += self.dx
            self.y += self.dy

            if self.x <= 0 or self.x >= self.screen_width:
                self.dx = -self.dx
            if self.y <= 0 or self.y >= self.screen_height:
                self.dy = -self.dy

            # 3. DEPLACEMENT
            try:
                pyautogui.moveTo(self.x, self.y)
            except pyautogui.FailSafeException:
                # Si la souris a été envoyée dans un coin de l'écran
                self.stop_from_thread()
                break
            except Exception:
                pass 
            
            time.sleep(0.02)

if __name__ == "__main__":
    root = tk.Tk()
    app = SafeMouseBouncer(root)
    root.mainloop()
