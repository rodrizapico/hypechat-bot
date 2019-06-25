from flask import Flask
from flask import request
from flask import json
from functools import reduce

import requests
import time

app = Flask(__name__)

if app.config['ENV'] == "development":
  baseUrl = 'http://api.hypechat:3000'
elif app.config['ENV'] == "production":
  baseUrl = 'https://hypechat-production.herokuapp.com'

@app.route('/ping')
def ping_pong():
  return 'pong'

def auth_expired(res):
  return res.status_code == 401 and res.json()['status'] == 'error' and res.json()['type'] == 'unauthorized'

def login():
  url = baseUrl + '/login'

  loginCredentials = {
    'email': 'titobot@hypechat.com',
    'password': 'titosPassword123!'
  }

  r = requests.post(url, json = loginCredentials)
  return r.json()['accessToken']

authToken = login()
silencedUntil = None

def default_message(received):
  return ('No comprendí el comando. Envía @Tito help para ver los comandos a los que puedo responder.')

def help_message(received):
  return ('Comandos: \n'
          '@Tito help - muestra este mensaje de ayuda.\n'
          '@Tito info - muestra información del grupo: integrantes, cantidad de mensajes, etc.\n'
          '@Tito mute <n> - desactiva mis respuestas por n segundos. Ejemplo: "@Tito mute 30" (máximo 300 segundos).\n'
          '@Tito me - muestra información sobre el usuario que envía el mensaje.')

def info_message(received):
  headers = {
    'X-Auth': authToken
  }

  url = baseUrl + '/workspaces/' + str(received['workspaceId']) + '/groups/' + str(received['groupId'])
  r = requests.get(url, headers = headers)
  groupData = r.json()

  # url = baseUrl + '/users/' + str(groupData['creatorId']) + '/profile'
  # r = requests.get(url, headers = headers)
  # creatorData = r.json()

  visibility = 'Público' if groupData['visibility'] == 'PUBLIC' else 'Privado' 

  def parse_member(member):
    annotation = (' (BOT)' if member['isBot'] else '')
    if not annotation:
      annotation = (' (CREADOR)' if member['id'] == groupData['creatorId'] else '')
    return member['firstName'] + ' ' + member['lastName'] + annotation


  members = list(map(parse_member, groupData['users']))

  print(groupData['users'], flush = True)
  print(members, flush = True)

  members = reduce(lambda a, b: a + ', ' + b, members)

  print(members, flush = True)

  return ('Nombre del grupo: ' + groupData['name'] + ' (' + visibility + ')\n'
          'Descripción: ' + groupData['description'] + '\n'
          'Fecha de creación: ' + groupData['createdAt'] + '\n'
          'Cantidad de mensajes: ' + str(groupData['totalMessages']) + '\n'
          'Miembros: ' + str(members) )

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

def me_message(received):
  url = baseUrl + '/users/' + str(received['from']['id']) + '/profile'
  r = requests.get(url)
  userData = r.json()

  userWorkspaces = list(map(lambda workspace: workspace['name'], userData['workspaces']))
  userWorkspaces = reduce(lambda a, b: a + '\n' + b, userWorkspaces)

  return ('Nombre completo: ' + userData['firstName'] + ' ' + userData['lastName'] + '\n'
          'Fecha de registro: ' + userData['regristationDate'] + '\n'
          'Workspaces a los que perteneces: \n' + str(userWorkspaces) )

def getAnswer(received):
  received['message_tokens'] = received['message'].split()
  if received['message_tokens'][0] != '@Tito' or len(received['message_tokens']) == 1:
    return default_message(received)
  return {
    'help': help_message,
    'info': info_message,
    'mute': mute_message,
    'me': me_message
  }.get(received['message_tokens'][1].lower(), default_message)(received)

def send_response(message, workspaceId, groupId):
  headers = {
    'X-Auth': authToken
  }

  payload = {
    'recipientId': None,
    'groupId': groupId,
    'message': message
  }

  url = baseUrl + '/workspaces/' + str(workspaceId) + '/messages'
  return requests.post(url, headers = headers, json = payload)

@app.route('/tito', methods=['POST'])
def tito():
  global authToken
  print("received: " + json.dumps(request.json), flush = True)

  # If bot is silenced, return.
  if silencedUntil and silencedUntil > time.time():
    return '200'

  # if mentioned by itself, Tito won't answer.
  if request.json['from']['firstName'] == 'Tito':
    return '200'

  time.sleep(1)

  anwser = getAnswer(request.json)
  r = send_response(anwser, request.json['workspaceId'], request.json['groupId'])

  if auth_expired(r):
    authToken = login()
    send_response(anwser)

  return '200'

@app.route('/tito/newmember', methods=['POST'])
def tito_greet():
  global authToken
  print("received: " + json.dumps(request.json), flush = True)

  # If bot is silenced, return.
  if silencedUntil and silencedUntil > time.time():
    return '200'

  # if new member is itself, Tito won't answer.
  if request.json['member']['firstName'] == 'Tito':
    return '200'

  time.sleep(1)

  print(request.json['member'], flush = True)
  answer = ('Bienvenido ' + request.json['member']['firstName'] + '!\n'
            'Soy un bot, y estoy para ayudarte.\n' 
            'Envía @Tito help para ver los comandos a los que puedo responder.')

  r = send_response(answer, request.json['workspaceId'], request.json['groupId'])

  if auth_expired(r):
    authToken = login()
    send_response(anwser)

  return '200'