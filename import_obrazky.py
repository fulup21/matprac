import os
import json
import base64

# Funkce pro získání čísla z názvu souboru
def ziskani_cisla(soubor: str) -> int:
    return int(os.path.splitext(soubor)[0])

# Funkce pro zakódování obrázku do base64
def kodovani_base64(soubor: str) -> str:
    # Otevření souboru v binárním režimu a jeho zakódování
    with open(soubor, "rb") as f:
        # Načteme obsah souboru a zakódujeme ho do base64
        obrazek_base64 = base64.b64encode(f.read()).decode("utf-8")
    return obrazek_base64

# Funkce pro získání všech obrázků a jejich uložení do seznamu
def ziskani_vsech_obrazku() -> list[dict[str, object]]:
    slozka = r"C:\Users\admin\Documents\Škola\MatPrac\obrazky"
    obrazky = []

    # Načtení všech souborů ve složce
    soubory = os.listdir(slozka)

    # Seřazení souborů podle čísla v názvu souboru
    soubory_serazene = sorted(soubory, key=ziskani_cisla)

    # Uložení souborů do seznamu
    for soubor in soubory_serazene:
        key = ziskani_cisla(soubor)
        cesta = os.path.join(slozka, soubor)
        base64_data = kodovani_base64(cesta)
        obrazky.append({"key": key, "path": cesta, "base64": base64_data})
    
    return obrazky

# Funkce pro uložení obrázků do JSON souboru
def ulozit_do_json(obrazky: list[dict[str, object]], soubor_json: str)->None:
    # Zapsat seznam obrázků do JSON souboru
    with open(soubor_json, "w", encoding="utf-8") as f:
        json.dump(obrazky, f, ensure_ascii=False, indent=4)

# Hlavní kód pro volání funkcí
slozka = r"C:\Users\admin\Documents\Škola\MatPrac\obrazky"
soubor_json = "obrazky.json"

# Získání všech obrázků do seznamu
obrazky = ziskani_vsech_obrazku()

# Uložení obrázků do JSON souboru
ulozit_do_json(obrazky, soubor_json)

print(f"Seznam obrázků byl úspěšně uložen do {soubor_json}")
