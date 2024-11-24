import base64

def encode_image(image_path:str)->str:
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

pic_path = "obrazky/1.png"

b64_pic = encode_image(pic_path)
print(b64_pic)