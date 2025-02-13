from random import random, shuffle
from abstrakt_hrac import AbstraktHrac, Karta
from sk import mujklic
import openai
import json
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk
import logging
openai.api_key=mujklic #api klic od openai

logging.basicConfig(filename='dixit.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s',filemode='w')  # 'w' mod nebo 'a' mod
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("dixit")

# upravit ui at je prehlednejsi
# multithreading



class SpravceKaret:
    mapa_karet: dict[int,Karta]= {}
    def __init__(self, soubor_json: str):
        """seznam, kam posleme vsechny karty"""


        with open(soubor_json, "r", encoding="utf-8") as s: # otevirame json soubor
            karty = json.load(s)
            for data_karty in karty:
                key = data_karty.get("key")
                path = data_karty.get("path")
                zakodovany_obrazek = data_karty.get("zakodovany_obrazek")

                karta = Karta(key=key, path=path, zakodovany_obrazek=zakodovany_obrazek)
                self.mapa_karet[key] = karta

    def najdi_kartu(self, klic:int)-> Karta:
        """najde kartu podle klice"""
        try: return self.mapa_karet[klic]
        except KeyError:
            raise ValueError(f"Karta s klicem: {klic} nebyla nalezena")

class Hrac(AbstraktHrac):
    """jednotlivi Chatgpt hraci"""


    def __init__(self,  jmeno:str, povaha: str = None, teplota:float = None)->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.povaha = povaha
        self.teplota = teplota
        self.jmeno = jmeno
        self.karty_ruka: list[Karta] = []
        self.skore = 0


    def seber_kartu(self, karta: Karta) -> None:
        self.karty_ruka.append(karta)

    def udelej_popis(self, karta:Karta)->str:
        prompt = """Na základě zadaného obrázku vytvoř abstraktní pojem 
        vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. 
        Vypiš mi pouze tento pojem a to ve formatu:'pojem'"""
        response = openai.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
            {
             "role": "developer",
             "content": f" jsi asistent, který odpovídá na dotazy v roli {self.povaha}"
            },
            {
              "role": "user",
              "content": [
                {"type": "text", "text": prompt},
                {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/png;base64,{karta.zakodovany_obrazek}",
                    "detail":"low",
                  },
                },
              ],
            }
          ],
          max_tokens=50, n=1, temperature= self.teplota
        )
        return response.choices[0].message.content

    def vyber_kartu(self, popis:str, vylozene_karty:list[Karta])->Karta:

        """podiva se na vsechny karty 'na stole' a porovna je se zdanim"""

        prompt = f"Na základě zadaných obrázků vyber ten, ktery nejlepe sedi zadanemu popisu:{popis}. Napis mi pouze cislo karty ve formatu:1"
        odpoved = [{
            "type": "text",
            "text": prompt,
        }]
        for i in range(len(vylozene_karty)):
            g = {"type": "image_url",
                 "image_url": {
                     "url": f"data:image/png;base64,{vylozene_karty[i].zakodovany_obrazek}",
                 "detail":"low"}}
            odpoved.append(g)

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "developer",
                    "content": f" jsi asistent, který odpovídá na dotazy v roli {self.povaha}"
                },
                {
                    "role": "user",
                    "content": odpoved,
                }
            ],
            max_tokens=300,
            n=1,
            temperature= self.teplota
        )
        return vylozene_karty[int(response.choices[0].message.content) - 1]
    def skoruj(self, cislo) -> None:
        self.skore += cislo


spravce = SpravceKaret("pokus.json")

class Hra:
    """Hra s jednim hrqcim kolem"""
    def __init__(self, pocet_hracu:int, jmena_hracu:list[str],root:tk.Tk,debug=False):
        self.debug = debug
        self.pocet_hracu = pocet_hracu
        self.jmena_hracu = jmena_hracu
        self.hraci: list[Hrac]= []
        self.povahy: list[str] = ["intelektuál", "farmář", "primitiv", "učitelka mateřské školky"]
        self.karty_v_balicku: list[Karta] = []
        self.bodovaci_stupnice = [0] * pocet_hracu # nemá smysl
        self.karty_v_odhazovaci_hromadce:list[Karta] = []
        self.karty_na_stole:list[tuple[Karta,Hrac]] = []
        self.pocet_karet_pro_hrace: int = 6  # Každý hráč dostane 6 karet
        self.pocet_kolo:int = 1
        self.index_vypravece:int = 0
        self.pozadi: list[str] = ['dodger blue', 'IndianRed1', 'slate blue', 'PaleGreen1']



        log.info("Spusteni aplikace")
        
        self.root = root
        self.root.geometry("1920x1200")
        self.root.title("Dixit Game")
        self.root.state("zoomed")

        self.canvas = Canvas(self.root)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create a bottom bar with a 'Play' button
        self.bottom_bar = tk.Frame(self.root, height=50, bg='lightgrey')
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.play_button = tk.Button(self.bottom_bar, text='Play', command=self.play_turn)
        self.play_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        self.log_button = tk.Button(self.bottom_bar, text="Log", command=self.show_log)
        self.log_button.pack(side=tk.LEFT, padx=2, pady=1)

        for i in range(self.pocet_hracu):
            self.hraci.append(Hrac(self.jmena_hracu[i],povaha=self.povahy[i % len(self.povahy)], teplota=random() + 0.5))

        self.zamichej_karty()
        self.rozdej_karty()
        self.canvas.after(100, self.center_text,)

    def center_text(self)->None:
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2, text="Simulace hry Dixit s openai", font=("Arial", 24), anchor=tk.CENTER)
        self.canvas.create_text(self.canvas.winfo_width() // 2, (self.canvas.winfo_height() // 2) + 30, text="Pro spustneni zmacknete tlacitko 'Play', pro zobrazeni logu zmacknete tlacitko 'Log'", font=("Arial", 18), anchor=tk.CENTER)

    def tah(self, index_vypravece)->None:
        """provede jeden tah, kdy jeden hrac je vybran vypravecem a ostatni hadaji"""
        if self.debug:
                    self.karty_na_stole.clear() # ujisti, ze tam nic neni

        vypravec :Hrac = self.hraci[index_vypravece]
        # vypravec_karta :Karta = vypravec.karty_ruka[0]  # vypravec vybere kartu, kterou bude popisovat

        vypravec_karta :Karta = vypravec.karty_ruka[0]
        
        popis :str = "sample popis dlouhy text bla bla bla"
        logging.info(f"Vypravec: {vypravec.jmeno}")
        logging.info(f"Vybrana karta: {vypravec_karta.key}, Popis: {popis}")
        

        self.karty_na_stole.append((vypravec_karta, vypravec))
        for hrac in self.hraci:
            if hrac != vypravec:
                vybrana_karta = hrac.karty_ruka[0]
                logging.info(f"Hrac {hrac.jmeno} vybral k popisu {popis} kartu: {vybrana_karta.key} a vylozil ji na stul")
                self.karty_na_stole.append((vybrana_karta, hrac))

        shuffle(self.karty_na_stole)
        
        hlasovani:list[tuple[Hrac,Karta]] = []
        for hrac in self.hraci:
            if hrac != vypravec:
                vybrana_karta = self.karty_na_stole[0][0]
                logging.info(f"Hrac {hrac.jmeno} hlasoval pro kartu: {vybrana_karta.key}")
                hlasovani.append((hrac, vybrana_karta))


        if not self.debug:
            self.karty_na_stole.clear() # ujisti, ze tam nic neni

            vypravec :Hrac = self.hraci[index_vypravece]
            vypravec_karta :Karta = vypravec.karty_ruka[0]  # vypravec vybere kartu, kterou bude popisovat


            popis :str = vypravec.udelej_popis(vypravec_karta)
            
            log.info(f"Vypravec: {vypravec.jmeno}")
            log.info(f"Vybrana karta: {vypravec_karta.key}, Popis: {popis}")
            self.karty_na_stole.append((vypravec_karta, vypravec))
            for hrac in self.hraci:
                if hrac != vypravec:
                    vybrana_karta = hrac.vyber_kartu(popis, hrac.karty_ruka)
                    self.karty_na_stole.append((vybrana_karta, hrac))
                    log.info(f"Hrac {hrac.jmeno} vybral k popisu {popis} kartu: {vybrana_karta.key} a vylozil ji na stul")



            shuffle(self.karty_na_stole)

            
            # Hraci, krome vypravece, hlasuji
            hlasovani:list[tuple[Hrac,Karta]] = []
            for hrac in self.hraci:
                if hrac != vypravec:
                    moznosti = [k[0] for k in self.karty_na_stole if k[1] != hrac]
                    vybrana_karta = hrac.vyber_kartu(popis, moznosti)
                    hlasovani.append((hrac, vybrana_karta))
                    log.info(f"Hrac {hrac.jmeno} hlasoval pro kartu: {vybrana_karta.key}")


            # # Výpočet bodů
            pocet_spravnych_hlasu = sum(1 for h in hlasovani if h[1] == vypravec_karta)

            if pocet_spravnych_hlasu == 0 or pocet_spravnych_hlasu == len(self.hraci) - 1:
                # Pokud všichni nebo nikdo neuhodl správně
                for hrac in self.hraci:
                    if hrac != vypravec:
                        hrac.skoruj(2)  # Přidej body nesprávně hádajícím hráčům
            else:
                vypravec.skoruj(3)  # Vypravěč dostává body
                for hrac, vybrana in hlasovani:
                    if vybrana == vypravec_karta:
                        hrac.skoruj(3)  # Hráči, kteří uhádli, dostanou body

                for karta, hrac in self.karty_na_stole:
                    if karta != vypravec_karta:
                        pro_hlasovali = sum(1 for h in hlasovani if h[1] == karta)
                        hrac.skoruj(pro_hlasovali)  # Hráči, jejichž karty byly vybrány, dostanou body

        # Display cards with the selected card highlighted
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        for idx, hrac in enumerate(self.hraci):
            col = idx % 2
            row = idx // 2
            x_offset = 50 + col * 600
            if col == 0:
                x_offset -= 20  # Move left column players to the left
            else:
                x_offset += 70  # Move right column players to the right

            y_offset = 80 + row * 450  # Move cards closer to the bottom

            # Draw a gray rectangle behind the player's name and cards
            rect_x1 = x_offset - 10
            rect_y1 = y_offset - 10
            rect_x2 = x_offset + 540  # Increase width by 100 pixels
            rect_y2 = y_offset + 130

            self.canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='lightgrey', outline='')

            # Draw a colored dot in front of the player's name
            circle_x1 = x_offset - 20
            circle_y1 = y_offset - 60
            circle_y2 = y_offset - 45
            circle_x2 = x_offset - 5  # Define circle_x2 to be slightly to the right of circle_x1
            self.canvas.create_oval(circle_x1, circle_y1, circle_x2, circle_y2, fill=self.pozadi[idx % len(self.pozadi)], outline='')

            # Include player's score in the display
            description_text = f'{hrac.jmeno} (Score: {hrac.skore})'
            if hrac == vypravec:
                description_text += f' - {popis}'
            self.canvas.create_text(x_offset, y_offset - 50, text=description_text, anchor='w', font=('Arial', 16, 'bold'))
            for card_idx, karta in enumerate(hrac.karty_ruka):
                x = x_offset + card_idx * 90  # Reduce spacing by decreasing the multiplier
                y = y_offset
                if karta.zakodovany_obrazek:
                    image = Image.open(karta.path)
                    image = image.resize((80, 120))
                    card_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(x + 40, y + 60, image=card_image)
                    if karta == vypravec_karta:
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline=self.pozadi[idx % len(self.pozadi)], width=5)
                    elif any(karta == k[0] for k in self.karty_na_stole):
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline=self.pozadi[idx % len(self.pozadi)], width=5)
                    if not hasattr(self, 'card_images'):
                        self.card_images = []
                    self.card_images.append(card_image)
                else:
                    self.canvas.create_rectangle(x, y, x + 80, y + 120, fill='white')
                    self.canvas.create_text(x + 40, y + 60, text=str(karta.key))
                    if karta == vypravec_karta:
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline='red', width=3)
                    elif any(karta == k[0] for k in self.karty_na_stole):
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline='yellow', width=3)
         

        """Blok karet urprostred"""

        # Calculate the starting position to center the cards on the canvas
        canvas_width = self.canvas.winfo_width()
        num_cards = len(self.karty_na_stole)
        card_width = 80  # Assuming each card is 80 pixels wide
        starting_x = (canvas_width - (num_cards * card_width + (num_cards - 1) * 10)) // 2

        # Display the cards side by side with a gap and outline
        for idx, (karta, hrac) in enumerate(self.karty_na_stole):
            x = starting_x + idx * (card_width + 10)  # Include the gap in the calculation
            y = self.canvas.winfo_height() // 2   # Adjust vertical position

            image = Image.open(karta.path)
            image = image.resize((80, 120))
            card_image = ImageTk.PhotoImage(image)
            # Draw outline with the player's color
            player_index = self.hraci.index(hrac)
            outline_color = self.pozadi[player_index % len(self.pozadi)]
            self.canvas.create_rectangle(x, y-80, x + 80, y + 60, fill = outline_color, outline=outline_color, width=3)
            self.canvas.create_image(x + 40, y, image=card_image)

            if not hasattr(self, 'card_images'):
                self.card_images = []
            self.card_images.append(card_image)
            self.canvas.create_text(x + 40, y - 60, text=hrac.jmeno, anchor='s', font=('Arial', 10, 'bold'))

            # Display the names of players who voted for the card below the card
            y_offset_text = y + 70  # Position text below the card
            for hlasujici_hrac, hlasovana_karta in hlasovani:
                if karta == hlasovana_karta:
                    self.canvas.create_text(x + 40, y_offset_text, text=hlasujici_hrac.jmeno, anchor='n', font=('Arial', 10))
                    y_offset_text += 15
        footer_text = tk.Label(self.bottom_bar, text=f'Probiha kolo cislo {self.pocet_kolo}, vypravec je {vypravec.jmeno}', bg='lightgrey', font=('Arial', 12, 'bold'))
        footer_text.pack(side=tk.BOTTOM, pady=10)
        self.canvas.update()

        # Remove selected cards from players' hands after updating the canvas
        for hrac in self.hraci:
            if hrac != vypravec:
                for vybrana_karta, _ in self.karty_na_stole:
                    if vybrana_karta in hrac.karty_ruka:
                        hrac.karty_ruka.remove(vybrana_karta)

        # Remove the vypravec_karta from the hand after updating the canvas
        vypravec.karty_ruka.remove(vypravec_karta)


        self.karty_v_odhazovaci_hromadce.extend([karta for karta, hrac in self.karty_na_stole])
        #da kartu ze stolu do odh. hromadku
        self.karty_na_stole.clear()

        if len(self.karty_v_balicku) < self.pocet_hracu * self.pocet_karet_pro_hrace: #jestli neni dost karet,dopln
            self.karty_v_balicku.extend(self.karty_v_odhazovaci_hromadce)
            self.karty_v_odhazovaci_hromadce.clear()

        for hrac in self.hraci:
                # Kazdemu hraci da jednu kartu, (lize si kartu)
                hrac.seber_kartu(self.karty_v_balicku.pop(0))

    def predzobrazeni(self):
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2, text=f"Predzobrazeni: probiha kolo cislo {self.pocet_kolo}", font=("Arial", 24, "bold"))

        self.card_images = []  # Ensure this list is initialized to store image references
        for idx, hrac in enumerate(self.hraci):
            col = idx % 2
            row = idx // 2
            x_offset = 50 + col * 600
            if col == 0:
                x_offset -= 20  # Move left column players to the left
            else:
                x_offset += 70  # Move right column players to the right

            y_offset = 80 + row * 450  # Adjusted y_offset for player blocks

            # Draw a gray rectangle behind the player's name and cards
            rect_x1 = x_offset - 10
            rect_y1 = y_offset - 10
            rect_x2 = x_offset + 540  # Adjust the width to fit the new card spacing
            rect_y2 = y_offset + 130  # Adjust the height if necessary
            self.canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='lightgrey', outline='')

            # Draw a colored dot in front of the player's name
            circle_x1 = x_offset - 20
            circle_y1 = y_offset - 60
            circle_y2 = y_offset - 45
            circle_x2 = x_offset - 5  # Define circle_x2 to be slightly to the right of circle_x1
            self.pozadi:list[str] = ['dodger blue', 'IndianRed1','slate blue','PaleGreen1']
            self.canvas.create_oval(circle_x1, circle_y1, circle_x2, circle_y2, fill=self.pozadi[idx % len(self.pozadi)], outline='')

            # Include player's score in the display
            description_text = f'{hrac.jmeno} (Score: {hrac.skore})'
            self.canvas.create_text(x_offset, y_offset - 50, text=description_text, anchor='w', font=('Arial', 16, 'bold'))
            for card_idx, karta in enumerate(hrac.karty_ruka):
                x = x_offset + card_idx * 90  # Adjusted spacing between cards
                y = y_offset
                if karta.zakodovany_obrazek:
                    image = Image.open(karta.path)
                    image = image.resize((80, 120))
                    card_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(x + 40, y + 60, image=card_image)
                    self.card_images.append(card_image)  # Store the reference to avoid garbage collection
                else:
                    self.canvas.create_rectangle(x, y, x + 80, y + 120, fill='white')
                    self.canvas.create_text(x + 40, y + 60, text=str(karta.key))

        self.canvas.update()

    def zamichej_karty(self)->None:
        for item in SpravceKaret.mapa_karet:
            self.karty_v_balicku.append(SpravceKaret.mapa_karet[item])
            shuffle(self.karty_v_balicku)
        log.info("Karty byly zamichany")

    def rozdej_karty(self):
        #Rozda karty
        log.info("Karty byly rozdany")
        # Ujistime se, ze mame dost karet v balicku
        if len(self.karty_v_balicku) < self.pocet_hracu * self.pocet_karet_pro_hrace:
            raise ValueError("Chyba s kartami, neni jich dost")

        for hrac in self.hraci:
            for i in range(self.pocet_karet_pro_hrace):
                # Kazdy hrac dostane svoji kartu
                hrac.seber_kartu(self.karty_v_balicku.pop(0))  # Vezmeme kartu z balicku a dame ji hraci

                # Jake karty dostal jaky hrac
                # print(f"Hráč {hrac.jmeno} dostal kartu {hrac.karty_ruka[-1].key}")


    def play_turn(self):
        # Step 1: Display the initial state with player names and cards
        for widget in self.bottom_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.destroy()
        self.predzobrazeni()
        log.info("@play_turn - Doslo k prvotnim zobrazeni karet pred kolem")
        # Step 2: Execute a turn, which includes the call to ChatGPT
        self.tah(self.index_vypravece)
        log.info("@play_turn -Doslo k tahu")
        self.index_vypravece += 1

        if self.index_vypravece >= len(self.hraci):         # jestli je index vypravece >= 4, odehralo se kolo a vypravec je znova ta sama osoba
            self.index_vypravece = 0
            self.pocet_kolo += 1
        
        

    def show_log(self):
        """Show the log window."""
        log_window = tk.Toplevel(self.root)
        log_window.title("Log")
        
        # Calculate size based on main window
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        window_width = int(main_width * 0.4)  # 40% of main window width
        window_height = int(main_height * 0.8)  # 80% of main window height (90% - 10%)
        
        # Calculate position (centered horizontally, 10% from top)
        x = self.root.winfo_x() + (main_width - window_width) // 2
        y = self.root.winfo_y() + int(main_height * 0.1)  # Start at 10% from top
        
        log_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        log_window.minsize(300, 400)
        
        # Create main frame for log window with padding
        log_frame = tk.Frame(log_window)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create text widget with scrollbars
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        log_text = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=log_text.yview)
        scrollbar_x = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=log_text.xview)
        
        log_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # Grid layout for text and scrollbars
        log_text.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # Load and display log content
        try:
            with open('dixit.log', 'r') as log_file:
                log_content = log_file.read()
                log_text.insert('1.0', log_content)
                log_text.config(state='disabled')  # Make text read-only
        except Exception as e:
            log_text.insert('1.0', f"Error reading log file: {str(e)}")
            log_text.config(state='disabled')
        
        # Add close button in its own frame at the bottom with more padding
        button_frame = tk.Frame(log_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        close_button = tk.Button(button_frame, text="Close", command=log_window.destroy)
        close_button.pack(pady=10, padx=5)

if __name__ == "__main__":
    root = tk.Tk()
    game = Hra(4, ["Petr", "Jana", "Josef", "Pavel"], root, debug=True)
    root.mainloop()
