from sk import mujklic
import openai
import json
from typing import Any

openai.api_key=mujklic

def ziskat_base64_pro_klic(soubor_json: str, klic: int) -> Any:
    # Otevru json soubor
    with open(soubor_json, "r", encoding="utf-8") as f:
        obrazky = json.load(f)

    # tu mas chybu, pretoze ti to vrati vzdy obrazok cislo 1
    # for obrazek in obrazky:
    #         return obrazek["base64"]
    #
    # je to lepsie urobit takto:

        if klic < len(obrazky)+1:
            try:
                base_64 = obrazky[klic-1]['base64']
                return(base_64)
            except:
                # index nenalezen
                return ""


# ziskas ty base64 data
base64_data = ziskat_base64_pro_klic("obrazky.json", 1)

if base64_data == "":
    print("Base64 nenalezen")
    exit(1)

prompt = "Jsi umelec, ktery poeticky popisuje obrazek.Snaz ze naznacit co je na obrazku ale nepopsat to doslovne. Rekni mi co je na tomto obrázku?"
prompt = "Co je na obrazku?"
prompt = "Jsi 18tileta holka, ktera ma umelecke citeni s romantickou dusi. Popis Co je na obrazku"
prompt = "Jsi 18tileta holka, ktera ma umelecke citeni s romantickou dusi. Popis Co je na obrazku bez toho aby si presne rekla co obrazek obzahuje, ale jen naznacila aby slo hadat co na obrazku skutecne je"

response = openai.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": prompt},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/png;base64,{base64_data}",
          },
        },
      ],
    }
  ],
  max_tokens=300,
)


print(response.choices[0].message.content)