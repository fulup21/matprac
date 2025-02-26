from random import random, shuffle
from abstrakt_hrac import AbstractPlayer, Card
from sk import mujklic
import openai
import json
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk
import logging
import threading
openai.api_key=mujklic # OpenAI API key

logging.basicConfig(filename='dixit.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s',filemode='w')  # 'w' mode or 'a' mode
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("dixit")

class CardManager:
    dict_of_cards: dict[int,Card]= {}
    def __init__(self, file_json: str):
        """list where we send all cards"""


        with open(file_json, "r", encoding="utf-8") as s: # opening JSON file
            cards = json.load(s)
            for card_data in cards:
                key = card_data.get("key")
                path = card_data.get("path")
                encoded_picture = card_data.get("encoded_picture")

                card = Card(key=key, path=path, encoded_picture=encoded_picture)
                self.dict_of_cards[key] = card

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
        prompt = """Na základě zadaného obrázku vytvoř abstraktní pojem 
        vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. 
        Vypiš mi pouze tento pojem a to ve formatu:'pojem'"""
        response = openai.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
            {
             "role": "developer",
             "content": f" jsi asistent, který odpovídá na dotazy v roli {self.nature}"
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
          max_tokens=50, n=1, temperature= self.temperature
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

manager = CardManager("pokus.json")

class DixitGame:
    """Game with one player round"""
    def __init__(self, number_of_players:int, names_of_players:list[str], root:tk.Tk, debug=False):
        self.debug = debug
        self.number_of_players = number_of_players
        self.names_of_players = names_of_players
        self.players: list[Player]= []
        self.natures: list[str] = ["intelektuál", "farmář", "primitiv", "učitelka mateřské školky"]
        self.cards_in_deck: list[Card] = []
        self.discard_pile:list[Card] = []
        self.cards_on_table:list[tuple[Card,Player]] = []
        self.number_of_cards_per_player: int = 6
        self.round_number:int = 1
        self.index_storyteller:int = 0
        self.backgrounds: list[str] = ['dodger blue', 'IndianRed1', 'slate blue', 'PaleGreen1']



        log.info("Application started")
        
        self.root = root
        self.root.geometry("1920x1200")
        self.root.title("Dixit Game")
        self.root.state("zoomed")

        self.canvas = Canvas(self.root)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create a bottom bar with a 'Play' button
        self.bottom_bar = tk.Frame(self.root, height=50, bg='lightgrey')
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.play_button = tk.Button(self.bottom_bar, text='Play', command=self.play_turn)
        self.play_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        self.log_button = tk.Button(self.bottom_bar, text="Log", command=self.show_log)
        self.log_button.pack(side=tk.LEFT, padx=2, pady=1)

        for i in range(self.number_of_players):
            self.players.append(Player(self.names_of_players[i], nature=self.natures[i % len(self.natures)], temperature=random() + 0.5))

        self.shuffle_cards()
        self.hand_out_cards()
        self.canvas.after(100, self.center_text,())

    def center_text(self, *args)->None:
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2, text="Simulace hry Dixit s openai", font=("Arial", 24), anchor=tk.CENTER)
        self.canvas.create_text(self.canvas.winfo_width() // 2, (self.canvas.winfo_height() // 2) + 30, text="Pro spustneni zmacknete tlacitko 'Play', pro zobrazeni logu zmacknete tlacitko 'Log'", font=("Arial", 18), anchor=tk.CENTER)

    def turn(self, storyteller_idx:int)->None:
        """perform one turn where one player is selected as the storyteller and others guess"""
        for widget in self.bottom_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.destroy()
        self.cards_on_table.clear() # make sure there's nothing there

        if self.debug:
            self.cards_on_table.clear()  # ujisti, ze tam nic neni

            storyteller: Player = self.players[storyteller_idx]
            # vypravec_karta :Card = vypravec.karty_ruka[0]  # vypravec vybere kartu, kterou bude popisovat

            storyteller_card: Card = storyteller.cards_on_hand[0]

            descripion: str = "sample popis dlouhy text bla bla bla"
            logging.info(f"Vypravec: {storyteller.name}")
            logging.info(f"Vybrana karta: {storyteller_card.key}, Popis: {descripion}")

            self.cards_on_table.append((storyteller_card, storyteller))
            for player in self.players:
                if player != storyteller:
                    chosen_card = player.cards_on_hand[0]
                    logging.info(
                        f"Hrac {player.name} vybral k popisu {descripion} kartu: {chosen_card.key} a vylozil ji na stul")
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
            def choose_card_thread(player):
                if player != storyteller:
                    chosen_card = player.choose_card(descripion, player.cards_on_hand)
                    self.cards_on_table.append((chosen_card, player))
                    log.info(f"Hrac {player.name} vybral k popisu {descripion} kartu: {chosen_card.key} a vylozil ji na stul")

            threads = []
            storyteller :Player = self.players[storyteller_idx]
            storyteller_card :Card = storyteller.cards_on_hand[0]  # storyteller chooses a card

            descripion :str = storyteller.make_description(storyteller_card)

            log.info(f"Vypravec: {storyteller.name}")
            log.info(f"Vybrana karta: {storyteller_card.key}, Popis: {descripion}")
            self.cards_on_table.append((storyteller_card, storyteller))

            for player in self.players:
                thread = threading.Thread(target=choose_card_thread, args=(player,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            shuffle(self.cards_on_table)

            # Players except storyteller vote
            def vote_thread(player):
                if player != storyteller:
                    choices = [k[0] for k in self.cards_on_table if k[1] != player]
                    chosen_card = player.choose_card(descripion, choices)
                    voting.append((player, chosen_card))
                    log.info(f"Hrac {player.name} hlasoval pro kartu: {chosen_card.key}")

            voting:list[tuple[Player,Card]] = []
            vote_threads = []
            for player in self.players:
                thread = threading.Thread(target=vote_thread, args=(player,))
                vote_threads.append(thread)
                thread.start()

            for thread in vote_threads:
                thread.join()

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

        # Display cards with the selected card highlighted
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.update_ui(storyteller, storyteller_card, descripion, voting)

        # Remove selected cards from players' hands after updating the canvas
        for player in self.players:
            if player != storyteller:
                for chosen_card, _ in self.cards_on_table:
                    if chosen_card in player.cards_on_hand:
                        player.cards_on_hand.remove(chosen_card)

        # Remove the vypravec_karta from the hand after updating the canvas
        storyteller.cards_on_hand.remove(storyteller_card)

        self.discard_pile.extend([card for card, player in self.cards_on_table])
        #da kartu ze stolu do odh. hromadku
        self.cards_on_table.clear()

        if len(self.cards_in_deck) < self.number_of_players * self.number_of_cards_per_player: #jestli neni dost karet,dopln
            self.cards_in_deck.extend(self.discard_pile)
            self.discard_pile.clear()

        for player in self.players:
                # Kazdemu hraci da jednu kartu, (lize si kartu)
                player.take_card(self.cards_in_deck.pop(0))

    def preview(self):
        for widget in self.bottom_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.destroy()
        self.canvas.delete('all')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2, text=f"Předzobrazení: vypočítává se kolo číslo  {self.round_number}", font=("Arial", 24, "bold"))

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
        for item in CardManager.dict_of_cards:
            self.cards_in_deck.append(CardManager.dict_of_cards[item])
            shuffle(self.cards_in_deck)
        log.info("Karty byly zamichany")

    def hand_out_cards(self):
        #Rozda karty
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

    def update_ui(self, storyteller:Player, storyteller_card:Card, descripion:str, voting:list[tuple[Player,Card]]):
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
                description_text += f' - {descripion}'
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
                               text=f'Probíha kolo číslo {self.round_number}, vypraveč je {storyteller.name}',
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
            message = f"Konec hry, vyhrali hraci {winner_names} s {max_score} body."
        else:
            message = f"Konec hry, vyhral hrac {winner_names} s {max_score} body."
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
    game = DixitGame(4, ["Petr", "Jana", "Josef", "Pavel"], root, debug=True)
    root.mainloop()
