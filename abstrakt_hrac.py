from abc import abstractmethod,ABC

from pydantic import BaseModel


class Card(BaseModel):
    """card with image, path, checksum for verification and encoded picture"""
    key:int
    path:str
    checksum: str
    encoded_picture: str

class AbstractPlayer(ABC):
    """Players"""
    
    @abstractmethod
    def __init__(self, name:str, nature: str | None, temperature: float | None)->None:
        """set how the player will behave"""
        self.nature = nature
        self.temperature = temperature
        self.name = name
        self.cards_on_hand:list[Card]=[]
        self.score: int = 0
        ...

    @abstractmethod
    def take_card(self, card:Card) -> None:
        """assign card to hand"""
        ...

    @abstractmethod
    def make_description(self, card:Card)->str:
        """make description for one card"""
        ...

    @abstractmethod
    def choose_card(self, description:str, laid_out_cards:list[Card])->Card:
        """look at all cards on the table and choose which one best fits the description"""
        ...

    @abstractmethod
    def score_add(self, number:int) -> None:
        """add score"""
        ...