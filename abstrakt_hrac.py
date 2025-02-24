from abc import abstractmethod,ABC

from pydantic import BaseModel


class Card(BaseModel):
    """jedna karta s obrazkem"""
    key:int
    path:str
    encoded_picture: str


class AbstractPlayer(ABC):
    """jednotlivi Chatgpt hraci"""
    cards_on_hand:list[Card]=[]
    score: int = 0

    @abstractmethod
    def __init__(self, name:str, nature: str | None, temperature: float | None)->None:
        """zde se nastavi jak se bude hrac chovat"""
        self.nature = nature
        self.temperature = temperature
        self.name = name
        ...

    @abstractmethod
    def take_card(self, card:Card) -> None:
        """prirad kartu do ruky"""
        ...

    @abstractmethod
    def make_description(self, card:Card)->str:
        """udela popis pro jednu kartu"""
        ...

    @abstractmethod
    def choose_card(self, description:str, laid_out_cards:list[Card])->Card:
        """podiva se na vsechny karty 'na stole' a porovna je se zdanim"""
        ...

    @abstractmethod
    def score_add(self, number:int) -> None:
        """prirad kartu do ruky"""
        ...