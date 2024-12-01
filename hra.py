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
    key:str
    path:str
    zakodovany_obrazek:str

    @staticmethod
    def nacti_karty(soubor_json:str)-> list["Karta"]:
        """nacte vsechny karty z json souboru, vytvori jejich instanci a ulozi do seznamu"""
        seznam_karet = []
        with open(soubor_json, "r", encoding="utf-8") as s:
            karty = json.load(s)
            for data_karty in karty:
                karta = Karta(key=data_karty.get("key"),path=data_karty.get("path"),zakodovany_obrazek=data_karty.get("base64"))
                seznam_karet.append(karta)
        return seznam_karet

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

# print(Karta.nacti_karty("obrazky.json")[0].path)
