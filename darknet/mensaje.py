import requests
from PIL import Image

ID_list = list()

bot_chatID = "-1001599456226"
bot_token = "1816131927:AAHWOWlreOkZs9xYQiu6w5vzxfwXuNvzpQ8"

def telegram_message(bot_chatID, bot_token, mensaje):
	send_text = "https://api.telegram.org/bot" + bot_token + "/sendMessage?chat_id=" + bot_chatID + "&parse_mode=MarkdownV2&text=" + str(mensaje)
	response = requests.get(send_text)
	return response.json()

def send_photo(chat_id, bot_token, image_path, image_caption=""):
    data = {"chat_id": chat_id, "caption": image_caption}
    url = "https://api.telegram.org/bot"+bot_token+"/sendPhoto"
    with open(image_path, "rb") as image_file:
        ret = requests.post(url, data=data, files={"photo": image_file})
    return ret.json()

# Envia los mensajes
def send_messages(imagen, mensaje):
    ''' 
    Envia la notificación a todos los usuarios agregados 
    
    Parámetros
    imagen: Imagen que se enviará a la notificación, se escribe en disco
    mensaje: Mensaje que se enviará como notificación
    '''
    im = Image.fromarray(imagen).save("Frame.jpeg")

    send_photo(bot_chatID, bot_token, "Frame.jpeg",mensaje)
