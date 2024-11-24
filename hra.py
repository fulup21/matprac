from sk import mujklic
import openai
import json
from typing import Any
from dataclasses import dataclass

openai.api_key=mujklic

@dataclass
class Karta:
    key:str
    path:str
    zakodovany_obrazek:str

    def nacti_karty(soubor_json:str)-> list["Karta"]:
        '''nacte vsechny karty z json souboru, vytvori jejich instanci a ulozi do seznamu'''
        seznam_karet = []
        with open(soubor_json, "r", encoding="utf-8") as s:
            karty = json.load(s)
            for data_karty in karty:
                karta = Karta(key=data_karty.get("key"),path=data_karty.get("path"),zakodovany_obrazek=data_karty.get("base64")), seznam_karet.append(karta)
        return seznam_karet
