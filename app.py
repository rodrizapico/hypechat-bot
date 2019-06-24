from flask import Flask
from flask import request
from flask import json
import requests
import time

app = Flask(__name__)

@app.route('/ping')
def ping_pong():
  return 'pong'

def auth_expired(res):
  return res.status_code == 401 and res.json()['status'] == 'error' and res.json()['type'] == 'unauthorized'

def login():
  loginUrl = 'http://api.hypechat:3000/login'

  loginCredentials = {
    'email': 'titobot@hypechat.com',
    'password': 'titosPassword123!'
  }

  r = requests.post(loginUrl, json = loginCredentials)
  return r.json()['accessToken']

authToken = login()
url = 'http://api.hypechat:3000/workspaces/1/messages'
silencedUntil = None

def help_message(received):
  return ('Comandos: \n'
          '@Tito help - muestra este mensaje de ayuda.\n'
          '@Tito info - muestra información del grupo: integrantes, cantidad de mensajes, etc.\n'
          '@Tito mute <n> - desactiva mis respuestas por n segundos. Ejemplo: "@Tito mute 30" (máximo 300 segundos).\n'
          '@Tito me - muestra información sobre el usuario que envía el mensaje.')

def default_message(received):
  return ('No comprendí el comando. Envía @tito help para ver los comandos a los que puedo responder.')

def mute_message(received):
  global silencedUntil

  if not received['message_tokens'][1].isdigit():
    return default_message(received)

  silencedTime = int(received['message_tokens'][1])
  if silencedTime > 300:
    message = ( 'Entendido, no responderé más comandos durante 300 segundos, '
                'el máximo tiempo que puedo permanecer silenciado' )
    silencedTime = 300
  else:
    message = ( 'Entendido, no responderé más comandos durante ' +
                str(silencedTime) +
                (' segundos' if silencedTime > 1 else ' segundo') )

  silencedUntil = time.time() + silencedTime
  return message

def getAnswer(received):

  received['message_tokens'] = received['message'].split()
  if len(received['message_tokens']) == 0 :
    return default_message(received)
  return {
    'help': help_message,
    'mute': mute_message,
  }.get(received['message_tokens'][0].lower(), default_message)(received)

def send_response(message):
  headers = {
    'X-Auth': authToken
  }

  payload = {
    'recipientId': None,
    'groupId': 1,
    'message': message
  }

  return requests.post(url, headers = headers, json = payload)

@app.route('/tito', methods=['POST'])
def tito_help():
  global authToken
  print("received: " + json.dumps(request.json), flush = True)

  # If bot is silenced, return.
  if silencedUntil and silencedUntil > time.time():
    return "200"

  time.sleep(1)

  anwser = getAnswer(request.json)
  r = send_response(anwser)

  if auth_expired(r):
    authToken = login()
    send_response(anwser)

  return "200"