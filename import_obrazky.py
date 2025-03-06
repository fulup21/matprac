import os
import json
import base64

from abstrakt_hrac import Card


def process_images_to_json(input_picture_directory: str, output_json_file: str) -> None:
    def get_num_from_name(file: str) -> int:
        return int(os.path.splitext(file)[0])

    def encode_to_b64(file: str) -> str:
        with open(file, "rb") as f:
            obrazek_base64: str = base64.b64encode(f.read()).decode("utf-8")
        return obrazek_base64

    pictures:list[Card] = []
    files:list[str] = os.listdir(input_picture_directory)
    sorted_files:list[str] = sorted(files, key=get_num_from_name)

    for file in sorted_files:
        key:int = get_num_from_name(file)
        path:str = os.path.join(input_picture_directory, file)
        base64_data:str = encode_to_b64(path)
        pictures.append(Card(key=key, path=path, encoded_picture=base64_data))

    json_data:str = json.dumps([picture.model_dump() for picture in pictures], ensure_ascii=False, indent=4) #pydantic
    with open(output_json_file, "w", encoding="utf-8") as f:
        f.write(json_data)

# Example usage
process_images_to_json(r"C:\Users\filip\Documents\Skola\matprac\obrazky", "obrazky.json")
