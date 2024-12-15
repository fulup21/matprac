from abc import abstractmethod,ABC
from dataclasses import dataclass


@dataclass
class Karta:
    """jedna karta s obrazkem"""
    key:int
    path:str
    zakodovany_obrazek:str


class AbstraktHrac(ABC):
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