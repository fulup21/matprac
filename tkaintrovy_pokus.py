from random import random, shuffle
from abstrakt_hrac import AbstractPlayer, Card
from import_obrazky import process_images_to_json
from sk import mujklic
import openai
import json
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk
import logging
import threading
import base64
import hashlib

openai.api_key=mujklic # OpenAI API key

### kontrolni soucet = checksum md5

logging.basicConfig(filename='dixit.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s',filemode='w')  # 'w' mode or 'a' mode
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("dixit")

class CardManager:
    
    def __init__(self, json_file: str, input_directory: str):
        self.dict_of_cards: dict[int, Card] = {}
        self.json_file = json_file
        self.input_directory = input_directory
        self.load_cards()

    def load_cards(self):
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Validate contents
            if not isinstance(data, list) or not all('key' in item and 'path' in item and 'checksum' in item and 'encoded_picture' in item for item in data):
                raise ValueError("JSON content is invalid")
            # Verify checksums
            for item in data:
                decoded_data = base64.b64decode(item['encoded_picture'].encode('utf-8'))
                calculated_checksum = hashlib.md5(decoded_data).hexdigest()
                if calculated_checksum != item['checksum']:
                    raise ValueError(f"Checksum verification failed for card with key {item['key']}")

            self.dict_of_cards = {item['key']: Card(**item) for item in data}
            log.info(f"Karty byly uspesne nacteny z '{self.json_file}'.")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            log.info(f"Error with JSON file '{self.json_file}': {e}. Regenerating...")
            process_images_to_json(self.input_directory, self.json_file)
            self.load_cards()  # Retry loading after regeneration

    def find_card(self, key:int)-> Card:
        """find a card by key"""
        try: return self.dict_of_cards[key]
        except KeyError:
            raise ValueError(f"Karta s klicem: {key} nebyla nalezena")

class Player(AbstractPlayer):
    """individual ChatGPT players"""

    def __init__(self, name:str, nature: str = None, temperature:float = None)->None:
        """this sets how the player will behave"""
        self.nature = nature
        self.temperature = temperature
        self.name = name
        self.cards_on_hand: list[Card] = []
        self.score = 0

    def take_card(self, card: Card) -> None:
        self.cards_on_hand.append(card)

    def make_description(self, card:Card)->str:
        prompt = """Na základě zadaného obrázku vytvoř abstraktní popis, neboli pojem 
        vystihující atmosféru a koncept obrázku, vyhni se přímému popisu detailů. Pojem nesmí být delší než 30 znaků.
        Vypiš mi pouze tento pojem a to ve formátu:'pojem'"""
        response = openai.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
            {
             "role": "user",
             "content": f" jsi asistent, který odpovídá na dotazy v roli {self.nature}, tvoje role by se mela odrazit v tom jak odpovidas"
            },
            {
              "role": "user",
              "content": [
                {"type": "text", "text": prompt},
                {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/png;base64,{card.encoded_picture}",
                    "detail":"low",
                  },
                },
              ],
            }
          ],
          max_tokens=75, n=1, temperature= self.temperature
        )
        return response.choices[0].message.content

    def choose_card(self, description:str, laid_out_cards:list[Card])->Card:

        """look at all cards 'on the table' and compare them with the description"""

        prompt = f"Na základě zadaných obrázků vyber ten, ktery nejlepe sedi zadanemu popisu:{description}. Napis mi pouze cislo karty ve formatu:1"
        built_message = [{
            "type": "text",
            "text": prompt,
        }]
        for i in range(len(laid_out_cards)):
            g = {"type": "image_url",
                 "image_url": {
                     "url": f"data:image/png;base64,{laid_out_cards[i].encoded_picture}",
                 "detail":"low"}}
            built_message.append(g)

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "developer",
                    "content": f" jsi asistent, který odpovídá na dotazy v roli {self.nature}"
                },
                {
                    "role": "user",
                    "content": built_message,
                }
            ],
            max_tokens=300,
            n=1,
            temperature= self.temperature
        )
        return laid_out_cards[int(response.choices[0].message.content) - 1]

    def score_add(self, number:int) -> None:
        self.score += number

manager = CardManager("pokus.json", r"C:\Users\filip\Documents\Skola\matprac\obrazky")

class DixitGame:
    """Game with one player round"""
    def __init__(self, names_of_players:list[str],natures: list[str], root:tk.Tk, debug=False):
        self.debug = debug
        self.number_of_players = 4
        self.names_of_players = names_of_players
        self.players: list[Player]= []
        self.natures = natures
        self.cards_in_deck: list[Card] = []
        self.discard_pile:list[Card] = []
        self.cards_on_table:list[tuple[Card,Player]] = []
        self.number_of_cards_per_player: int = 6
        self.round_number:int = 1
        self.index_storyteller:int = 0
        self.backgrounds: list[str] = ['dodger blue', 'IndianRed1', 'slate blue', 'PaleGreen1']
        self.card_images:list[ImageTk]=[]

        log.info("Zacatek aplikace")
        
        self.root = root
        self.root.geometry("1920x1200")
        self.root.title("Dixit Game")
        self.root.state("zoomed")

        self.canvas = Canvas(self.root)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create a bottom bar with a 'Play' button
        self.bottom_bar = tk.Frame(self.root, height=50, bg='lightgrey')
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.start_game_button = tk.Button(self.canvas, text='Začít hru', font=("Arial", 60), command=self.play_turn)
        self.start_game_button.place(relx=0.5, rely=0.7, anchor=tk.CENTER)
        
        self.play_button = tk.Button(self.bottom_bar, text='Zahraj další tah', command=self.play_turn)
        
        self.log_button = tk.Button(self.bottom_bar, text="Log", command=self.show_log)
        self.log_button.pack(side=tk.LEFT, padx=2, pady=1)

        for i in range(self.number_of_players):
            self.players.append(Player(self.names_of_players[i], nature=self.natures[i % len(self.natures)], temperature=random() + 0.5))

        for player in self.players:
            log.info(f'Vytvoren hrac jmenem {player.name} s povahou {player.nature} a temperature {player.temperature}')

        self.shuffle_cards()
        self.hand_out_cards()
        self.canvas.after(100, self.center_text,())

    def center_text(self, *args)->None:
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2 - 200, text="Simulace hry Dixit s openai", font=("Arial", 60), anchor=tk.CENTER)
        self.canvas.create_text(self.canvas.winfo_width() // 2, (self.canvas.winfo_height() // 2) - 130, text="Pro spustení zmáčkněte tlačítko 'Začít hru', pro zobrazení logu zmacknete tlačítko 'Log'", font=("Arial", 18), anchor=tk.CENTER)

    def turn(self, storyteller_idx:int)->None:
        """perform one turn where one player is selected as the storyteller and others guess"""
        for widget in self.bottom_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.destroy()
        self.cards_on_table.clear() # make sure there's nothing there
        self.play_button.pack(side=tk.RIGHT, padx=10, pady=10)

        if self.debug:
            storyteller: Player = self.players[storyteller_idx]
            storyteller_card: Card = storyteller.cards_on_hand[0]

            description: str = "sample popis dlouhy text bla bla bla"
            logging.info(f"Vypravec: {storyteller.name}")
            logging.info(f"Vybrana karta: {storyteller_card.key}, Popis: {description}")

            self.cards_on_table.append((storyteller_card, storyteller))
            for player in self.players:
                if player != storyteller:
                    chosen_card = player.cards_on_hand[0]
                    logging.info(
                        f"Hrac {player.name} vybral k popisu {description} kartu: {chosen_card.key} a vylozil ji na stul")
                    self.cards_on_table.append((chosen_card, player))

            shuffle(self.cards_on_table)

            voting: list[tuple[Player, Card]] = []
            for player in self.players:
                if player != storyteller:
                    chosen_card = self.cards_on_table[0][0]
                    logging.info(f"Hrac {player.name} hlasoval pro kartu: {chosen_card.key}")
                    voting.append((player, chosen_card))

            for player in self.players:
                player.score_add(2)
        else:
            threads = []
            storyteller :Player = self.players[storyteller_idx]
            storyteller_card :Card = storyteller.cards_on_hand[0]  # storyteller chooses a card

            description :str = storyteller.make_description(storyteller_card)

            log.info(f"Vypravec: {storyteller.name}")
            log.info(f"Vybrana karta: {storyteller_card.key}, Popis: {description}")
            self.cards_on_table.append((storyteller_card, storyteller))

            for player in self.players:
                thread = threading.Thread(target=self.choose_card_thread, args=(player,storyteller,description,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            shuffle(self.cards_on_table)

            # Players except storyteller vote
            voting:list[tuple[Player,Card]] = []
            vote_threads = []
            for player in self.players:
                thread = threading.Thread(target=self.vote_thread, args=(player,storyteller,description,voting,))
                vote_threads.append(thread)
                thread.start()

            for thread in vote_threads:
                thread.join()

            self.calculate_scores(voting, storyteller, storyteller_card)

        # clear the canvas
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        #show the updated UI
        self.update_ui(storyteller, storyteller_card, description, voting)
        #remove cards from players' hands, clear cards on the table and give a new card to the players
        self.prepare_next_round()

    def choose_card_thread(self,player:Player,storyteller:Player,description:str):
                if player != storyteller:
                    chosen_card = player.choose_card(description, player.cards_on_hand)
                    self.cards_on_table.append((chosen_card, player))
                    log.info(f"Hrac {player.name} vybral k popisu {description} kartu: {chosen_card.key} a vylozil ji na stul")
    
    def vote_thread(self,player:Player,storyteller:Player,description:str,voting:list[tuple[Player,Card]]):
                if player != storyteller:
                    choices = [k[0] for k in self.cards_on_table if k[1] != player]
                    chosen_card = player.choose_card(description, choices)
                    voting.append((player, chosen_card))
                    log.info(f"Hrac {player.name} hlasoval pro kartu: {chosen_card.key}")
        
    def prepare_next_round(self):
        # Remove selected cards from players' hands after updating the canvas
        for player in self.players:
            for chosen_card, _ in self.cards_on_table:
                if chosen_card in player.cards_on_hand:
                    player.cards_on_hand.remove(chosen_card)

        self.discard_pile.extend([card for card, player in self.cards_on_table])
        #adds the discarded cards to the discard pile
        self.cards_on_table.clear()

        if len(self.cards_in_deck) < self.number_of_players * self.number_of_cards_per_player: #jestli neni dost karet,dopln
            self.cards_in_deck.extend(self.discard_pile)
            self.discard_pile.clear()

        for player in self.players:
                # each player gets a card
                player.take_card(self.cards_in_deck.pop(0))

    def calculate_scores(self, voting: list[tuple[Player, Card]], storyteller: Player, storyteller_card: Card) -> None:
                    # score calculation
            number_of_correct_votes = sum(1 for h in voting if h[1] == storyteller_card)

            if number_of_correct_votes == 0 or number_of_correct_votes == len(self.players) - 1:
                # If everyone or no one guessed correctly
                for player in self.players:
                    if player != storyteller:
                        player.score_add(2)  # Add points to the wrong guessers
            else:
                storyteller.score_add(3)  # storyteller gets points
                for player, chosen_card in voting:
                    if chosen_card == storyteller_card:
                        player.score_add(3)  # player gets points for choosing the right card

            for card, player in self.cards_on_table:
                if card != storyteller_card:
                    for_voted = sum(1 for h in voting if h[1] == card)
                    player.score_add(for_voted)  # player gets points for voting for the card

    def preview(self):
        self.start_game_button.destroy()
        for widget in self.bottom_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.destroy()
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2, text=f"Vypočítává se tah hráče {self.players[self.index_storyteller].name}", font=("Arial", 24, "bold"))
        footer_text = tk.Label(self.bottom_bar,
                               text=f'Probíha kolo číslo {self.round_number}, vypraveč je {self.players[self.index_storyteller].name}',
                               bg='lightgrey', font=('Arial', 12, 'bold'))
        footer_text.pack(side=tk.BOTTOM, pady=10)

        self.card_images = []  # Ensure this list is initialized to store image references
        for idx, player in enumerate(self.players):
            col = idx % 2
            row = idx // 2
            x_offset = 50 + col * 600
            if col == 0:
                x_offset -= 20  # Move left column players to the left
            else:
                x_offset += 70  # Move right column players to the right

            y_offset = 80 + row * 450  # Adjusted y_offset for player blocks

            # Draw a gray rectangle behind the player's name and cards
            rect_x1 = x_offset - 10
            rect_y1 = y_offset - 10
            rect_x2 = x_offset + 540  # Adjust the width to fit the new card spacing
            rect_y2 = y_offset + 130  # Adjust the height if necessary
            self.canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='lightgrey', outline='')

            # Draw a colored dot in front of the player's name
            circle_x1 = x_offset - 20
            circle_y1 = y_offset - 60
            circle_y2 = y_offset - 45
            circle_x2 = x_offset - 5  # Define circle_x2 to be slightly to the right of circle_x1
            self.backgrounds:list[str] = ['dodger blue', 'IndianRed1', 'slate blue', 'PaleGreen1']
            self.canvas.create_oval(circle_x1, circle_y1, circle_x2, circle_y2, fill=self.backgrounds[idx % len(self.backgrounds)], outline='')

            # Include player's score in the display
            description_text = f'{player.name} (Skóre: {player.score})'
            self.canvas.create_text(x_offset, y_offset - 50, text=description_text, anchor='w', font=('Arial', 16, 'bold'))
            for card_idx, card in enumerate(player.cards_on_hand):
                x = x_offset + card_idx * 90  # Adjusted spacing between cards
                y = y_offset
                if card.encoded_picture:
                    image = Image.open(card.path)
                    image = image.resize((80, 120))
                    card_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(x + 40, y + 60, image=card_image)
                    self.card_images.append(card_image)  # Store the reference to avoid garbage collection
                else:
                    self.canvas.create_rectangle(x, y, x + 80, y + 120, fill='white')
                    self.canvas.create_text(x + 40, y + 60, text=str(card.key))

        self.canvas.update()

    def shuffle_cards(self)->None:
        for item in manager.dict_of_cards:
            self.cards_in_deck.append(manager.dict_of_cards[item])
            shuffle(self.cards_in_deck)
        log.info("Karty byly zamichany")

    def hand_out_cards(self):
        #Hands out cards
        log.info("Karty byly rozdany")
        # Ujistime se, ze mame dost karet v balicku
        if len(self.cards_in_deck) < self.number_of_players * self.number_of_cards_per_player:
            raise ValueError("Chyba s kartami, neni jich dost")

        for player in self.players:
            for i in range(self.number_of_cards_per_player):
                # Kazdy hrac dostane svoji kartu
                player.take_card(self.cards_in_deck.pop(0))  # Take a card from the deck and give it to the player

    def play_turn(self):
        # Step 1: Display the initial state with player names and cards
        max_score = max(player.score for player in self.players)
        if max_score >= 30:
            self.game_end(max_score)
        else: 
            self.preview()
            log.info("@play_turn - Doslo k prvotnim zobrazeni karet pred kolem")
            # Step 2: Execute a turn, which includes the call to ChatGPT
            self.turn(self.index_storyteller)
            log.info("@play_turn - Doslo k tahu")
            self.index_storyteller += 1

        if self.index_storyteller >= len(self.players):   # if the index_storyteller is greater than or equal to the number of players, 
            self.index_storyteller = 0                     # reset it and increase the round number
            self.round_number += 1

    def update_ui(self, storyteller:Player, storyteller_card:Card, description:str, voting:list[tuple[Player,Card]]):
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        for idx, player in enumerate(self.players):
            col = idx % 2
            row = idx // 2
            x_offset = 50 + col * 600
            x_offset += -20 if col == 0 else 70
            y_offset = 80 + row * 450

            self.canvas.create_rectangle(x_offset - 10, y_offset - 10, x_offset + 540, y_offset + 130, fill='lightgrey',
                                         outline='')
            self.canvas.create_oval(x_offset - 20, y_offset - 60, x_offset - 5, y_offset - 45,
                                    fill=self.backgrounds[idx % len(self.backgrounds)], outline='')

            description_text = f'{player.name} (Skóre: {player.score})'
            if player == storyteller:
                description_text += f' - {description}'
            self.canvas.create_text(x_offset, y_offset - 50, text=description_text, anchor='w',
                                    font=('Arial', 16, 'bold'))

            for card_idx, card in enumerate(player.cards_on_hand):
                x, y = x_offset + card_idx * 90, y_offset
                if card.encoded_picture:
                    image = Image.open(card.path).resize((80, 120))
                    card_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(x + 40, y + 60, image=card_image)
                    outline_color = self.backgrounds[idx % len(self.backgrounds)] if card == storyteller_card or any(
                        card == k[0] for k in self.cards_on_table) else None
                    if outline_color:
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline=outline_color, width=5)
                    if not hasattr(self, 'card_images'):
                        self.card_images = []
                    self.card_images.append(card_image)
                else:
                    self.canvas.create_rectangle(x, y, x + 80, y + 120, fill='white')
                    self.canvas.create_text(x + 40, y + 60, text=str(card.key))
                    outline_color = 'red' if card == storyteller_card else 'yellow' if any(
                        card == k[0] for k in self.cards_on_table) else None
                    if outline_color:
                        self.canvas.create_rectangle(x, y, x + 80, y + 120, outline=outline_color, width=3)

        canvas_width = self.canvas.winfo_width()
        num_cards = len(self.cards_on_table)
        starting_x = (canvas_width - (num_cards * 80 + (num_cards - 1) * 10)) // 2

        for idx, (card, player) in enumerate(self.cards_on_table):
            x, y = starting_x + idx * (80 + 10), self.canvas.winfo_height() // 2
            image = Image.open(card.path).resize((80, 120))
            card_image = ImageTk.PhotoImage(image)
            outline_color = self.backgrounds[self.players.index(player) % len(self.backgrounds)]
            self.canvas.create_rectangle(x, y - 80, x + 80, y + 60, fill=outline_color, outline=outline_color, width=3)
            self.canvas.create_image(x + 40, y, image=card_image)
            if not hasattr(self, 'card_images'):
                self.card_images = []
            self.card_images.append(card_image)
            self.canvas.create_text(x + 40, y - 60, text=player.name, anchor='s', font=('Arial', 10, 'bold'))

            y_offset_text = y + 70
            for voting_player, voted_card in voting:
                if card == voted_card:
                    self.canvas.create_text(x + 40, y_offset_text, text=voting_player.name, anchor='n',
                                            font=('Arial', 10))
                    y_offset_text += 15

        footer_text = tk.Label(self.bottom_bar,
                               text=f'Proběhlo kolo číslo {self.round_number}, vypraveč je {storyteller.name}',
                               bg='lightgrey', font=('Arial', 12, 'bold'))
        footer_text.pack(side=tk.BOTTOM, pady=10)
        self.canvas.update()
        
    def show_log(self):
        """Show the log window."""
        log_window = tk.Toplevel(self.root)
        log_window.title("Log")
        
        # Calculate size based on main window
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        window_width = int(main_width * 0.4)  # 40% of main window width
        window_height = int(main_height * 0.8)  # 80% of main window height (90% - 10%)
        
        # Calculate position (centered horizontally, 10% from top)
        x = self.root.winfo_x() + (main_width - window_width) // 2
        y = self.root.winfo_y() + int(main_height * 0.1)  # Start at 10% from top
        
        log_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        log_window.minsize(300, 400)
        
        # Create main frame for log window with padding
        log_frame = tk.Frame(log_window)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create text widget with scrollbars
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        log_text = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=log_text.yview)
        scrollbar_x = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=log_text.xview)
        
        log_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # Grid layout for text and scrollbars
        log_text.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # Load and display log content
        try:
            with open('dixit.log', 'r') as log_file:
                log_content = log_file.read()
                log_text.insert('1.0', log_content)
                log_text.config(state='disabled')  # Make text read-only
        except Exception as e:
            log_text.insert('1.0', f"Error reading log file: {str(e)}")
            log_text.config(state='disabled')
        
        # Add close button in its own frame at the bottom with more padding
        button_frame = tk.Frame(log_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        close_button = tk.Button(button_frame, text="Close", command=log_window.destroy)
        close_button.pack(pady=10, padx=5)

    def game_end(self, max_score:int):
        winners = [hrac for hrac in self.players if hrac.score == max_score]
        winner_names = ', '.join(hrac.name for hrac in winners)
        if len(winners) > 1:
            message = f"Konec hry, vyhráli hráči {winner_names} s {max_score} body."
        else:
            message = f"Konec hry, vyhrál hráč {winner_names} s {max_score} body."
        self.display_winner_message(message)

    def display_winner_message(self, message):
        for widget in self.bottom_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.destroy()
        self.canvas.delete('all')
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2, text=message, font=("Arial", 24), anchor=tk.CENTER)
        self.play_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    jmena_hracu=  ["Petr", "Jana", "Josef", "Pavel"]
    povahy_hracu = ["odpovídáš jako voják", "odpovídáš jako tří leté dítě","mluvíš pozpátku", "si slovák, odpovídej slovensky"]
    game = DixitGame( jmena_hracu, povahy_hracu, root, debug=False)
    root.mainloop()
