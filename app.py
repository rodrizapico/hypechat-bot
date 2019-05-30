from flask import Flask
import requests
import time

app = Flask(__name__)

@app.route('/ping')
def ping_pong():
  return 'pong'

@app.route('/tito', methods=['POST'])
def tito_help():
  time.sleep(1)
  url = 'http://api.hypechat:3000/workspaces/1/messages'

  headers = {
    'X-Auth': 'Pi0BqihRDjhjtLi46gvLrrWAt9AgMvZvWWCttopgPcL11RXuDGTbFQIJRyux66A3eVDIhW6lTZnfzIxxsCY4BB93TBQKRLRxg5f3wc5Lumb4D7WauZ6WudvxQRBoKiEN'
  }

  message = ( 'Usage: \n'
              '@tito help - muestra este mensaje de ayuda.\n'
              '@tito info - muestra información del canal: integrantes, cantidad de mensajes, etc.\n'
              '@tito mute <n> - desactiva el bot por n segundos (ejemplo: "@tito mute 30").\n'
              '@tito me - muestra información sobre el usuario que envía el mensaje.' )
  payload = {
    'recipientId': None,
    'groupId': 1,
    'message': message
  }

  r = requests.post(url, headers = headers, json = payload)
  return "200"