from random import random, shuffle

from abstrakt_hrac import AbstraktHrac, Karta

from sk import mujklic
import openai
import json
# from typing import Any



openai.api_key=mujklic



class SpravceKaret:
    mapa_karet: dict[int,Karta]= {}
    def __init__(self, soubor_json:str):
        """seznam, kam posleme vsechny karty"""


        with open(soubor_json, "r", encoding="utf-8") as s:
            karty = json.load(s)
            for data_karty in karty:
                karta = Karta(key=data_karty.get("key"),path=data_karty.get("path"),zakodovany_obrazek=data_karty.get("base64"))
                self.mapa_karet[karta.key] = karta


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


    def najdi_kartu(self, klic:int)-> Karta:
        """najde kartu podle klice"""
        try: return self.mapa_karet[klic]
        except KeyError:
            raise ValueError(f"Karta s klicem: {klic} nebyla nalezena")

class Hrac(AbstraktHrac):
    """jednotlivi Chatgpt hraci"""
    karty_ruka: list[Karta] = []
    skore = 0

    def __init__(self, povaha: str = None, teplota:float = None )->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.povaha = povaha
        self.teplota = teplota

    def seber_kartu(self, karta: Karta.key) -> None:
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
        # for i in range(0, len(response.choices)):
        #     seznam.append(int(response.choices[i].message.content))
        return vylozene_karty[int(response.choices[0].message.content) - 1]
    def skoruj(self, cislo) -> None:
        self.skore += 1


spravce = SpravceKaret("obrazky.json")


# def vytvor_popis(klic_karty:int)-> list[str]:
#     """vytvori popis pro jednu karty na zaklade klice"""
#     prompt = "Na základě zadaného obrázku vytvoř abstraktní pojem vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. Vypiš mi pouze tento pojem a to ve formatu:'pojem'"
#     response = openai.chat.completions.create(
#       model="gpt-4o-mini",
#       messages=[
#         {
#           "role": "user",
#           "content": [
#             {"type": "text", "text": prompt},
#             {
#               "type": "image_url",
#               "image_url": {
#                 "url": f"data:image/png;base64,{spravce.najdi_kartu(klic_karty).zakodovany_obrazek}",
#               },
#             },
#           ],
#         }
#       ],
#       max_tokens=50, n=4, temperature= 1
#     )
#
#     seznam:list[str]=[]
#
#     for i in range(0,4):
#         seznam.append(response.choices[i].message.content)
#     return seznam

# def vyber_obrazek(vylozene_karty:list[Karta], popis)->Karta:
#     prompt = f"Na základě zadaných obrázků vyber ten, ktery nejlepe sedi zadanemu popisu:{popis}. Napis mi pouze cislo karty ve formatu:1"
#     #seznam: list[str] = []
#
#     odpoved = [{
#           "type": "text",
#           "text": prompt,
#         }]
#     for i in range(len(vylozene_karty)):
#         g = {"type": "image_url",
#           "image_url": {
#             "url": f"data:image/png;base64,{vylozene_karty[i].zakodovany_obrazek}"}}
#         odpoved.append(g)
#
#     response = openai.chat.completions.create(
#         model="gpt-4o-mini",
#         messages= [
#     {
#       "role": "user",
#       "content": odpoved,
#     }
#   ],
#         max_tokens=300,
#         n=1
#     )
#     # for i in range(0, len(response.choices)):
#     #     seznam.append(int(response.choices[i].message.content))
#     return vylozene_karty[int(response.choices[0].message.content)-1]


#list_s_kartami = [spravce.najdi_kartu(16), spravce.najdi_kartu(17), spravce.najdi_kartu(18),spravce.najdi_kartu(19),spravce.najdi_kartu(20)]


# h = Hrac(teplota= 0)
# k = spravce.najdi_kartu(6)
# p = h.udelej_popis(k)
# g = h.vyber_kartu("Heboucke",list_s_kartami).key
# print(p)
# for o in SpravceKaret.seznam_karet:
#     list_s_kartami.append(spravce.najdi_kartu(o))
# # for i in list_s_kartami:
# #     print(i.key)
# print(h.vyber_kartu(p, list_s_kartami).key)

class Hra:
    """Hra s jednim hrqcim kolem"""
    hraci:list[Hrac] = [] #seznam hracu ve hre
    povahy:list[str] = ["intelektuál","farmář","primitiv","učitelka mateřské školky"] #povahy pro hrace
    karty_na_stole:list[Karta] = [] #karty vylozene na stole
    karty_v_balicku:list[Karta] = []
    pocet_kolo = 1


    def __init__(self, pocet_hracu):
        self.pocet_hracu = pocet_hracu
        for i in range(0,self.pocet_hracu-1):
            self.hraci.append(Hrac(povaha=self.povahy[i],teplota=random()+0.5))

    def zamichej_karty(self)->None:
        for item in SpravceKaret.mapa_karet:
            self.karty_v_balicku.append(SpravceKaret.mapa_karet[item])
            shuffle(self.karty_v_balicku)

    def rozdej_karty(self):
        pocitadlo_hracu: int = 0
        for hrac in self.hraci:
            for i in range(1,5):
                hrac.seber_kartu(self.karty_v_balicku[i+pocitadlo_hracu*4-1])
                print(i+pocitadlo_hracu*4-1) # logger pro samotare
            pocitadlo_hracu += 1


    def tah(self):
        """Provede jeden tah, ve kterem je jeden hac vypravec, """


    def kolo(self):

        if self.pocet_kolo == 1:
            for hrac in self.hraci:


        for hrac in self.hraci:
            if hrac.skore > 30:
                self.konec_hry(self.hraci.index(hrac) - 1)
                return


    @staticmethod
    def konec_hry(cislo)->None:
        print(f'vyhrava hrac cislo {cislo}')