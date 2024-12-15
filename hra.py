from abc import abstractmethod

from sk import mujklic
import openai
import json
# from typing import Any
from dataclasses import dataclass


openai.api_key=mujklic

@dataclass
class Karta:
    """jedna karta s obrazkem"""
    key:int
    path:str
    zakodovany_obrazek:str

class SpravceKaret:

    """seznam, kam posleme vsechny karty"""
    seznam_karet: list[Karta] = []

    @staticmethod
    def nacti_karty(soubor_json:str)-> list["Karta"]:
        """nacte vsechny karty z json souboru, vytvori jejich instanci a ulozi do seznamu"""
        if not SpravceKaret.seznam_karet:
            with open(soubor_json, "r", encoding="utf-8") as s:
                karty = json.load(s)
                for data_karty in karty:
                    karta = Karta(key=data_karty.get("key"),path=data_karty.get("path"),zakodovany_obrazek=data_karty.get("base64"))
                    SpravceKaret.seznam_karet.append(karta)
            return SpravceKaret.seznam_karet

    @staticmethod
    def najdi_kartu(klic:int)-> Karta:
        """najde kartu podle klice"""
        for karta in SpravceKaret.seznam_karet:
            if karta.key == klic:
                return karta
        raise ValueError(f"Karta s klicem: {klic} nebyla nalezena")

class Hrac:
    """jednotlivi Chatgpt hraci"""
    @abstractmethod
    def __init__(self, povaha: str|None, teplota:float|None )->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.povaha = povaha
        self.teplota = teplota
        ...

    @abstractmethod
    def udelej_popis(self, karta:Karta)->str:
        """udela popis pro jednu kartu"""
        ...

    @abstractmethod
    def vyber_kartu(self, popis:str, vylozene_karty:list[Karta])->Karta:
        """podiva se na vsechny karty 'na stole' a porovna je se zdanim"""
        ...
spravce = SpravceKaret
spravce.nacti_karty("obrazky.json")

# print(spravce.najdi_kartu(5).path)
# print(SpravceKaret.najdi_kartu(1).path)

# prompt = "Na základě zadaného obrázku vytvoř abstraktní pojem vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. Vypiš mi pouze tento pojem a to ve formatu:'pojem'"
# response = openai.chat.completions.create(
#   model="gpt-4o-mini",
#   messages=[
#     {
#       "role": "user",
#       "content": [
#         {"type": "text", "text": prompt},
#         {
#           "type": "image_url",
#           "image_url": {
#             "url": f"data:image/png;base64,{Karta.nacti_karty("obrazky.json")[0].zakodovany_obrazek}",
#           },
#         },
#       ],
#     }
#   ],
#   max_tokens=50, n=4
# )
#
#
# for i in range(0,4):
#     print(response.choices[i].message.content)

def vytvor_popis(klic_karty:int)-> list[str]:
    """vytvori popis pro jednu karty na zaklade klice"""
    prompt = "Na základě zadaného obrázku vytvoř abstraktní pojem vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. Vypiš mi pouze tento pojem a to ve formatu:'pojem'"
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
                "url": f"data:image/png;base64,{spravce.najdi_kartu(klic_karty).zakodovany_obrazek}",
              },
            },
          ],
        }
      ],
      max_tokens=50, n=4, temperature= 1
    )

    seznam:list[str]=[]

    for i in range(0,4):
        seznam.append(response.choices[i].message.content)
    return seznam

def vyber_obrazek(vylozene_karty:list[Karta], popis)->list[str]:
    prompt = f"Na základě zadaných obrázků vyber ten, ktery nejlepe sedi zadanemu popisu:{popis}. Napis mi pouze cislo karty ve formatu:'1'"
    seznam: list[str] = []

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
        messages= [
    {
      "role": "user",
      "content": odpoved,
    }
  ],
        max_tokens=300,
        n=4
    )
    for i in range(0, 4):
        seznam.append(response.choices[i].message.content)
    return seznam


list_s_kartami = [spravce.najdi_kartu(1),spravce.najdi_kartu(2),spravce.najdi_kartu(3),spravce.najdi_kartu(6)]

print(vyber_obrazek(list_s_kartami,"starec"))

#print(vytvor_popis(6))

