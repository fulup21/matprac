import tkinter as tk
from tkinter import Scrollbar, Canvas
import os
import random
from PIL import Image, ImageTk
import openai
import base64
from sk import mujklic

# Set OpenAI API Key
openai.api_key = mujklic

CARD_FOLDER = "obrazky"
CARD_SIZE = (100, 150)
PLAYER_COUNT = 4
CARDS_PER_PLAYER = 5


class DixitGame:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1400x1100")
        self.root.title("Dixit Game")

        self.canvas = Canvas(self.root)
        self.scrollbar = Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.players = [f"Player {i + 1}" for i in range(PLAYER_COUNT)]
        random.shuffle(self.players)
        self.story_teller = self.players[0]
        self.cards = self.load_cards()
        self.player_hands = self.deal_cards()
        self.selected_cards = {}
        self.progress_label = tk.Label(root, text="Starting...", font=("Arial", 14))
        self.progress_label.pack(pady=50)

        # Start the progress
        self.update_progress("Startuji aplikaci")
        self.create_ui()

    def update_progress(self, progress):
        # Update the label with progress text
        self.progress_label.config(text=f"{progress}")


    def load_cards(self):
        card_paths = [os.path.join(CARD_FOLDER, img) for img in os.listdir(CARD_FOLDER) if img.endswith(".png")]
        random.shuffle(card_paths)
        return card_paths

    def deal_cards(self):
        hands = {}
        used_cards = set()
        for player in self.players:
            hands[player] = []
            while len(hands[player]) < CARDS_PER_PLAYER:
                card = random.choice(self.cards)
                if card not in used_cards:
                    hands[player].append(card)
                    used_cards.add(card)
        return hands

    def create_ui(self):
        tk.Label(self.scrollable_frame, text=f"Storyteller: {self.story_teller}", font=("Arial", 14, "bold"),
                 pady=10).pack()

        for player in self.players:
            frame = tk.Frame(self.scrollable_frame)
            frame.pack(pady=5)
            tk.Label(frame, text=player, font=("Arial", 12)).pack()
            card_frame = tk.Frame(frame)
            card_frame.pack()

            for card_path in self.player_hands[player]:
                img = Image.open(card_path).resize(CARD_SIZE)
                img = ImageTk.PhotoImage(img)
                card_label = tk.Label(card_frame, image=img, borderwidth=2, relief="solid")
                card_label.image = img
                if player == self.story_teller:
                    card_label.bind("<Button-1>", lambda e, c=card_path: self.select_story_card(c))
                card_label.pack(side="left", padx=5)

        self.selected_frame = tk.Frame(self.scrollable_frame)
        self.selected_frame.pack(pady=10)
        tk.Label(self.selected_frame, text="Selected Cards", font=("Arial", 12, "bold")).pack()
        self.selected_card_frame = tk.Frame(self.selected_frame)
        self.selected_card_frame.pack()

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def select_story_card(self, card_path):
        if self.story_teller not in self.selected_cards:
            self.selected_cards[self.story_teller] = card_path
            self.describe_card(card_path)


    def udelej_popis(self, path)->str:
        prompt = """Na základě zadaného obrázku vytvoř abstraktní pojem 
        vystihující atmosféru a koncept obrázku, vyhni se popisu detailů. 
        Vypiš mi pouze tento pojem a to ve formatu:'pojem'"""
        with open(path, "rb") as image_file:
            # Read the image data in binary mode
            image_data = image_file.read()

            # Encode the image data to base64
        zakodovany_obrazek = base64.b64encode(image_data).decode('utf-8')


        response = openai.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
            {
             "role": "developer",
             "content": f" jsi asistent, který odpovídá na dotazy v roli intelektuala"
            },
            {
              "role": "user",
              "content": [
                {"type": "text", "text": prompt},
                {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/png;base64,{zakodovany_obrazek}",
                  },
                },
              ],
            }
          ],
          max_tokens=50, n=1, temperature=0.9
        )
        print(f"Obrazok z cesty {path} ma popis:  ")
        print(response.choices[0].message.content)
        return response.choices[0].message.content
    def describe_card(self, card_path):

        self.update_progress(f"Delam popisek karty {card_path}")

        description = self.udelej_popis(card_path)
        self.update_progress(f"Popisek je: {description}")


        tk.Label(self.scrollable_frame, text=f"Storyteller's Description: {description}", font=("Arial", 12, "italic"),
                 pady=5).pack()

        root.after(100,lambda:self.find_matching_cards(description))
        #self.find_matching_cards(description)

    def vyber_kartu(self, popis: str, player):

            if player != self.story_teller:
                """podiva se na vsechny karty 'na stole' a porovna je se zdanim"""

                prompt = f"Na základě zadaných obrázků vyber ten, ktery nejlepe sedi zadanemu popisu:{popis}. Napis mi pouze cislo karty ve formatu:1"
                odpoved = [{
                    "type": "text",
                    "text": prompt,
                }]
                for card in self.player_hands[player]:

                    with open(card, "rb") as image_file:
                        # Read the image data in binary mode
                        image_data = image_file.read()

                        # Encode the image data to base64
                        zakodovany_obrazek = base64.b64encode(image_data).decode('utf-8')

                        g = {"type": "image_url",
                             "image_url": {
                                 "url": f"data:image/png;base64,{zakodovany_obrazek}"}}
                        odpoved.append(g)

                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "developer",
                            "content": f" jsi asistent, který odpovídá na dotazy v roli intelektual"
                        },
                        {
                            "role": "user",
                            "content": odpoved,
                        }
                    ],
                    max_tokens=300,
                    n=1,
                    temperature=0.9
                )
                selected_card = self.player_hands[player][int(response.choices[0].message.content) - 1]
            return selected_card
    def find_matching_cards(self, description):
        for player in self.players:
            if player != self.story_teller:
                self.update_progress(f'Pro hrace {player} hledam kartu')
                print(f'Pro hrace {player} hledam kartu')
                # prompt = f"Based on the given description: '{description}', choose the most relevant image from these options."
                # images = [open(card, "rb").read() for card in self.player_hands[player]]
                #
                # response = openai.ChatCompletion.create(
                #     model="gpt-4o-mini",
                #     messages=[
                #         {"role": "system", "content": "You are an AI that selects the most relevant image."},
                #         {"role": "user", "content": prompt}
                #     ],
                #     max_tokens=5
                # )
                # selected_card = self.player_hands[player][int(response["choices"][0]["message"]["content"]) - 1]
                selected_card = self.vyber_kartu(description, player)
                self.selected_cards[player] = selected_card
        self.display_selected_cards()

    def display_selected_cards(self):
        for widget in self.selected_card_frame.winfo_children():
            widget.destroy()
        for player, card_path in self.selected_cards.items():
            frame = tk.Frame(self.selected_card_frame)
            frame.pack(side="left", padx=5)
            img = Image.open(card_path).resize(CARD_SIZE)
            img = ImageTk.PhotoImage(img)
            card_label = tk.Label(frame, image=img, borderwidth=2, relief="solid")
            card_label.image = img
            card_label.pack()
            tk.Label(frame, text=player, font=("Arial", 10)).pack()


if __name__ == "__main__":
    root = tk.Tk()
    game = DixitGame(root)
    root.mainloop()
