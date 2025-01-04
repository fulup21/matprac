from abc import abstractmethod,ABC

from pydantic import BaseModel


class Karta(BaseModel):
    """jedna karta s obrazkem"""
    key:int
    path:str
    zakodovany_obrazek: str


class AbstraktHrac(ABC):
    """jednotlivi Chatgpt hraci"""
    karty_ruka:list[Karta]=[]
    skore: int = 0

    @abstractmethod
    def __init__(self, jmeno:str, povaha: str|None, teplota:float|None)->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.povaha = povaha
        self.teplota = teplota
        self.jmeno = jmeno
        ...

    @abstractmethod
    def seber_kartu(self, karta:Karta) -> None:
        """prirad kartu do ruky"""
        ...

    @abstractmethod
    def udelej_popis(self, karta:Karta)->str:
        """udela popis pro jednu kartu"""
        ...

    @abstractmethod
    def vyber_kartu(self, popis:str, vylozene_karty:list[Karta])->Karta:
        """podiva se na vsechny karty 'na stole' a porovna je se zdanim"""
        ...

    @abstractmethod
    def skoruj(self, cislo) -> None:
        """prirad kartu do ruky"""
        ...