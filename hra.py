from random import random, shuffle
from abstrakt_hrac import AbstractPlayer, Card
from sk import mujklic
import openai
import json



openai.api_key=mujklic #api klic od openai



class SpravceKaret:
    mapa_karet: dict[int,Card]= {}
    def __init__(self, soubor_json: str):
        """seznam, kam posleme vsechny karty"""


        with open(soubor_json, "r", encoding="utf-8") as s: # otevirame json soubor
            karty = json.load(s)
            for data_karty in karty:
                key = data_karty.get("key")
                path = data_karty.get("path")
                zakodovany_obrazek = data_karty.get("zakodovany_obrazek")

                karta = Card(key=key, path=path, zakodovany_obrazek=zakodovany_obrazek)
                self.mapa_karet[key] = karta


    # @staticmethod
    # def nacti_karty(soubor_json:str)-> list["Karta"]:
    #     """nacte vsechny karty z json souboru, vytvori jejich instanci a ulozi do seznamu"""
    #     if not SpravceKaret.seznam_karet:
    #         with open(soubor_json, "r", encoding="utf-8") as s:
    #             karty = json.load(s)
    #             for data_karty in karty:
    #                 karta = Karta(key=data_karty.get("key"),path=data_karty.get("path"),zakodovany_obrazek=data_karty.get("base64"))
    #                 SpravceKaret.seznam_karet.append(karta)
    #         return SpravceKaret.seznam_karet


    def najdi_kartu(self, klic:int)-> Card:
        """najde kartu podle klice"""
        try: return self.mapa_karet[klic]
        except KeyError:
            raise ValueError(f"Karta s klicem: {klic} nebyla nalezena")

class Hrac(AbstractPlayer):
    """jednotlivi Chatgpt hraci"""


    def __init__(self, name:str, nature: str = None, temperature:float = None)->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.povaha = nature
        self.teplota = temperature
        self.jmeno = name
        self.karty_ruka: list[Card] = []
        self.skore = 0


    def take_card(self, card: Card) -> None:
        self.karty_ruka.append(card)

    def make_description(self, card:Card)->str:
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
                    "url": f"data:image/png;base64,{card.encoded_picture}",
                  },
                },
              ],
            }
          ],
          max_tokens=50, n=1, temperature= self.teplota
        )
        return response.choices[0].message.content

    def choose_card(self, description:str, laid_out_cards:list[Card])->Card:

        """podiva se na vsechny karty 'na stole' a porovna je se zdanim"""

        prompt = f"Na základě zadaných obrázků vyber ten, ktery nejlepe sedi zadanemu popisu:{description}. Napis mi pouze cislo karty ve formatu:1"
        odpoved = [{
            "type": "text",
            "text": prompt,
        }]
        for i in range(len(laid_out_cards)):
            g = {"type": "image_url",
                 "image_url": {
                     "url": f"data:image/png;base64,{laid_out_cards[i].encoded_picture}",
                 }}
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
        # for i in range(0, len(response.choices)):
        #     seznam.append(int(response.choices[i].message.content))
        return laid_out_cards[int(response.choices[0].message.content) - 1]
    def score_add(self, number) -> None:
        self.skore += number


spravce = SpravceKaret("pokus.json")

class Hra:
    """Hra s jednim hrqcim kolem"""
    def __init__(self, pocet_hracu:int, jmena_hracu:list[str]):
        self.pocet_hracu = pocet_hracu
        self.jmena_hracu = jmena_hracu
        self.hraci: list[Hrac]= []
        self.povahy: list[str] = ["intelektuál", "farmář", "primitiv", "učitelka mateřské školky"]
        self.karty_v_balicku: list[Card] = []
        self.bodovaci_stupnice = [0] * pocet_hracu
        self.karty_v_odhazovaci_hromadce:list[Card] = []
        self.karty_na_stole:list[tuple[Card,Hrac]] = []
        self.pocet_karet_pro_hrace = 6  # Každý hráč dostane 6 karet
        self.pocet_kolo = 1

        for i in range(self.pocet_hracu):
            self.hraci.append(Hrac(self.jmena_hracu[i], nature=self.povahy[i % len(self.povahy)], temperature=random() + 0.5))

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
                hrac.take_card(self.karty_v_balicku.pop(0))  # Vezmeme kartu z balicku a dame ji hraci

                # Jake karty dostal jaky hrac
                # print(f"Hráč {hrac.jmeno} dostal kartu {hrac.karty_ruka[-1].key}")



    def tah(self, vypravec_index):
        """provede jeden tah, kdy jeden hrac je vybran vypravecem a ostatni hadaji"""

        self.karty_na_stole.clear() # ujisti, ze tam nic neni
        print("DALSI TAH!!!!!!!!!!")
        vypravec :Hrac = self.hraci[vypravec_index]
        vypravec_karta :Card = vypravec.karty_ruka.pop(0)  # vypravec vybere kartu, kterou bude popisovat
        print(f'Vypravec je {vypravec.jmeno} a vybira kartu: {vypravec_karta.key}')
        popis :str = vypravec.make_description(vypravec_karta)
        print(f'Popis od vypravece je:{popis}')

        # ostatni hraci vybiraji kartu dle napovedy
        self.karty_na_stole.append((vypravec_karta, vypravec))
        for hrac in self.hraci:
            if hrac != vypravec:


                print(f'hrac {hrac.jmeno} ma karty:') # logovani jake karty kdo ma
                jake_karty_ma:list[int] = []
                for k in hrac.karty_ruka:
                    jake_karty_ma.append(k.key)
                print(jake_karty_ma)

                vybrana_karta = hrac.choose_card(popis, hrac.karty_ruka)
                print(f'A vybral kartu cislo:{vybrana_karta.key}')
                hrac.karty_ruka.remove(vybrana_karta)  # vybrana karta je vylozena na stul a odebrana z ruky
                self.karty_na_stole.append((vybrana_karta, hrac))


        shuffle(self.karty_na_stole)

        # Hraci, krome vypravece, hlasuji
        hlasovani:list[tuple[Hrac,Card]] = []
        for hrac in self.hraci:
            if hrac != vypravec:
                moznosti = [k[0] for k in self.karty_na_stole if k[1] != hrac]
                vybrana_karta = hrac.choose_card(popis, moznosti)
                print(f'hrac {hrac.jmeno} vybral kartu {vybrana_karta.key}')
                hlasovani.append((hrac, vybrana_karta))

        # Výpočet bodů
        pocet_spravnych_hlasu = sum(1 for h in hlasovani if h[1] == vypravec_karta)

        if pocet_spravnych_hlasu == 0 or pocet_spravnych_hlasu == len(self.hraci) - 1:
            # Pokud všichni nebo nikdo neuhodl správně
            for hrac in self.hraci:
                if hrac != vypravec:
                    hrac.score_add(2)  # Přidej body nesprávně hádajícím hráčům
        else:
            vypravec.score_add(3)  # Vypravěč dostává body
            for hrac, vybrana in hlasovani:
                if vybrana == vypravec_karta:
                    hrac.score_add(3)  # Hráči, kteří uhádli, dostanou body

            for karta, hrac in self.karty_na_stole:
                if karta != vypravec_karta:
                    pro_hlasovali = sum(1 for h in hlasovani if h[1] == karta)
                    hrac.score_add(pro_hlasovali)  # Hráči, jejichž karty byly vybrány, dostanou body
        self.karty_v_odhazovaci_hromadce.extend([karta for karta, hrac in self.karty_na_stole])
        #da kartu ze stolu do odh. hromadku
        self.karty_na_stole.clear()

        if len(self.karty_v_balicku) < self.pocet_hracu * self.pocet_karet_pro_hrace: #jestli neni dost karet,dopln
            self.karty_v_balicku.extend(self.karty_v_odhazovaci_hromadce)
            self.karty_v_odhazovaci_hromadce.clear()

        for hrac in self.hraci:
                # Kazdemu hraci da jednu kartu, (lize si kartu)
                hrac.take_card(self.karty_v_balicku.pop(0))

        for hrac in self.hraci:
            print(f"Hráč {hrac.jmeno} má skóre: {hrac.skore}")


    def kolo(self):
        """jedno kolo, ve kterem kazdy hrac odehraje tah"""

        if self.pocet_kolo == 1: #pokud je to prvni kolo, rozdej a zamichej karty
            self.zamichej_karty()
            self.rozdej_karty()


    @staticmethod
    def konec_hry(cislo)->None:
        print(f'vyhrava hrac cislo {cislo}')

ajmena_hracu = ["Alice", "Bob", "Charlie", "Diana"]
hra = Hra(pocet_hracu=4, jmena_hracu=ajmena_hracu)

hra.kolo()