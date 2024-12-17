from abstrakt_hrac import AbstraktHrac, Karta

from sk import mujklic
import openai
import json
# from typing import Any



openai.api_key=mujklic



class SpravceKaret:
    seznam_karet: dict = {}
    def __init__(self, soubor_json:str):
        """seznam, kam posleme vsechny karty"""


        with open(soubor_json, "r", encoding="utf-8") as s:
            karty = json.load(s)
            for data_karty in karty:
                karta = Karta(key=data_karty.get("key"),path=data_karty.get("path"),zakodovany_obrazek=data_karty.get("base64"))
                self.seznam_karet[karta.key] = karta


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
        try: return self.seznam_karet[klic]
        except KeyError:
            raise ValueError(f"Karta s klicem: {klic} nebyla nalezena")

class Hrac(AbstraktHrac):
    """jednotlivi Chatgpt hraci"""
    def __init__(self, povaha: str = None, teplota:float = None )->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.povaha = povaha
        self.teplota = teplota

    def udelej_popis(self, karta:Karta)->str:
        prompt = """Na základě zadaného obrázku vytvoř abstraktní pojem 
        vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. 
        Vypiš mi pouze tento pojem a to ve formatu:'pojem'"""
        response = openai.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
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
          max_tokens=50, n=1, temperature= 1
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


list_s_kartami = [spravce.najdi_kartu(20),spravce.najdi_kartu(4),spravce.najdi_kartu(17),spravce.najdi_kartu(9)]

h = Hrac(teplota= 2)
k = spravce.najdi_kartu(13)
print(h.vyber_kartu("maly princ", list_s_kartami).key)
