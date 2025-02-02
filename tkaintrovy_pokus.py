from random import random, shuffle
from abstrakt_hrac import AbstraktHrac, Karta
from sk import mujklic
import openai
import json
import tkinter as tk
from tkinter import Scrollbar, Canvas
import os
from PIL import Image, ImageTk
import threading
openai.api_key=mujklic #api klic od openai



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
                     "url": f"data:image/png;base64,{vylozene_karty[i].zakodovany_obrazek}"}}
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
    def __init__(self, pocet_hracu:int, jmena_hracu:list[str],root):
        self.pocet_hracu = pocet_hracu
        self.jmena_hracu = jmena_hracu
        self.hraci: list[Hrac]= []
        self.povahy: list[str] = ["intelektuál", "farmář", "primitiv", "učitelka mateřské školky"]
        self.karty_v_balicku: list[Karta] = []
        self.bodovaci_stupnice = [0] * pocet_hracu
        self.karty_v_odhazovaci_hromadce:list[Karta] = []
        self.karty_na_stole:list[tuple[Karta,Hrac]] = []
        self.pocet_karet_pro_hrace = 6  # Každý hráč dostane 6 karet
        self.pocet_kolo = 1

        self.root = root
        self.root.geometry("1400x1100")
        self.root.title("Dixit Game")
        self.root.state("zoomed")

        self.canvas = Canvas(self.root)

        for i in range(self.pocet_hracu):
            self.hraci.append(Hrac(self.jmena_hracu[i],povaha=self.povahy[i % len(self.povahy)], teplota=random() + 0.5))

        self.zamichej_karty()
        self.rozdej_karty()

        # Create a PLAY button
        self.play_button = tk.Button(self.root, text='PLAY', command=self.play_turn)
        self.play_button.pack()

    def tah(self, index_vypravece):
        """provede jeden tah, kdy jeden hrac je vybran vypravecem a ostatni hadaji"""
        self.karty_na_stole.clear() # ujisti, ze tam nic neni

        vypravec :Hrac = self.hraci[index_vypravece]
        vypravec_karta :Karta = vypravec.karty_ruka[0]  # vypravec vybere kartu, kterou bude popisovat

        popis :str = vypravec.udelej_popis(vypravec_karta)

        self.karty_na_stole.append((vypravec_karta, vypravec))
        for hrac in self.hraci:
            if hrac != vypravec:
                vybrana_karta = hrac.vyber_kartu(popis, hrac.karty_ruka)
                self.karty_na_stole.append((vybrana_karta, hrac))

        shuffle(self.karty_na_stole)

        # Hraci, krome vypravece, hlasuji
        hlasovani:list[tuple[Hrac,Karta]] = []
        for hrac in self.hraci:
            if hrac != vypravec:
                vybrana_karta = hrac.vyber_kartu(popis, [k[0] for k in self.karty_na_stole])
                hlasovani.append((hrac, vybrana_karta))

        # Výpočet bodů
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
            y_offset = 80 + row * 300

            # Include player's score in the display
            description_text = f'{hrac.jmeno} (Score: {hrac.skore})'
            if hrac == vypravec:
                description_text += f' - {popis}'
            self.canvas.create_text(x_offset, y_offset - 50, text=description_text, anchor='w', font=('Arial', 16, 'bold'))
            for card_idx, karta in enumerate(hrac.karty_ruka):
                x = x_offset + card_idx * 100
                y = y_offset
                if karta.zakodovany_obrazek:
                    image = Image.open(karta.path)
                    image = image.resize((80, 120))
                    card_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(x + 40, y + 60, image=card_image)
                    if karta == vypravec_karta:
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline='red', width=3)
                    elif any(karta == k[0] for k in self.karty_na_stole):
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline='yellow', width=3)
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

                # Display the names of players who voted for the card below the card
                y_offset_text = y + 140
                for hlasujici_hrac, hlasovana_karta in hlasovani:
                    if karta == hlasovana_karta:
                        self.canvas.create_text(x + 40, y_offset_text, text=hlasujici_hrac.jmeno, anchor='n', font=('Arial', 10))
                        y_offset_text += 15

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

        
    def zamichej_karty(self)->None:
        for item in SpravceKaret.mapa_karet:
            self.karty_v_balicku.append(SpravceKaret.mapa_karet[item])
            shuffle(self.karty_v_balicku)

    def rozdej_karty(self):
        #Rozda karty

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
        # Execute a turn
        self.tah(0)

if __name__ == "__main__":
    root = tk.Tk()
    game = Hra(4, ["Petr", "Jana", "Josef", "Pavel"], root)
    root.mainloop()
