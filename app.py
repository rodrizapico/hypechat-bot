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

def login(loginCredentials):
  url = baseUrl + '/login'

  r = requests.post(url, json = loginCredentials)
  return r.json()['accessToken']

titoLoginCredentials = {
  'email': 'titobot@hypechat.com',
  'password': 'titosPassword123!'
}

titoAuthToken = login(titoLoginCredentials)
maxSilenceTime = 600
silencedUntil = None

def get_group_data(workspaceId, groupId):
  global titoAuthToken
  url = baseUrl + '/workspaces/' + str(workspaceId) + '/groups/' + str(groupId)
  r = requests.get(url, headers = { 'X-Auth': titoAuthToken })

  if auth_expired(r):
    titoAuthToken = login(titoLoginCredentials)
    requests.get(url, headers = { 'X-Auth': titoAuthToken })

  return r.json()

def get_user_data(userId):
  url = baseUrl + '/users/' + str(userId) + '/profile'
  r = requests.get(url)
  return r.json()

def post_response(message, workspaceId, groupId):
  global titoAuthToken

  url = baseUrl + '/workspaces/' + str(workspaceId) + '/messages'
  payload = {
    'recipientId': None,
    'groupId': groupId,
    'message': message
  }

  r = requests.post(url, headers = { 'X-Auth': titoAuthToken }, json = payload)

  if auth_expired(r):
    titoAuthToken = login(titoLoginCredentials)
    requests.post(url, headers = { 'X-Auth': titoAuthToken }, json = payload)

def default_message(received):
  return ('No comprendí el comando. Envía @Tito help para ver los comandos a los que puedo responder.')

def help_message(received):
  return ('Comandos: \n'
          '@Tito help - muestra este mensaje de ayuda.\n'
          '@Tito info - muestra información del grupo: integrantes, cantidad de mensajes, etc.\n'
          '@Tito mute <n> - desactiva mis respuestas por n segundos. Ejemplo: "@Tito mute 30" (máximo 300 segundos).\n'
          '@Tito me - muestra información sobre el usuario que envía el mensaje.')

def info_message(received):
  groupData = get_group_data(received['workspaceId'], received['groupId'])

  visibility = 'Público' if groupData['visibility'] == 'PUBLIC' else 'Privado' 

  def parse_member(member):
    annotation = (' (BOT)' if member['isBot'] else '')
    if not annotation:
      annotation = (' (CREADOR)' if member['id'] == groupData['creatorId'] else '')
    return member['firstName'] + ' ' + member['lastName'] + annotation

  members = list(map(parse_member, groupData['users']))
  members = reduce(lambda a, b: a + ', ' + b, members)

  return ('Nombre del grupo: ' + groupData['name'] + ' (' + visibility + ')\n'
          'Descripción: ' + groupData['description'] + '\n'
          'Fecha de creación: ' + groupData['createdAt'] + '\n'
          'Cantidad de mensajes: ' + str(groupData['totalMessages']) + '\n'
          'Miembros: ' + str(members) )

def mute_message(received):
  global silencedUntil

  if not received['message_tokens'][2].isdigit():
    return default_message(received)

  silencedTime = int(received['message_tokens'][2])
  if silencedTime > maxSilenceTime:
    message = ( 'Entendido, no responderé más comandos durante ' + str(maxSilenceTime) + ' segundos, '
                'el máximo tiempo que puedo permanecer silenciado' )
    silencedTime = maxSilenceTime
  else:
    message = ( 'Entendido, no responderé más comandos durante ' +
                str(silencedTime) +
                (' segundos' if silencedTime > 1 else ' segundo') )

  silencedUntil = time.time() + silencedTime
  return message

def me_message(received):
  userData = get_user_data(received['from']['id'])
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

@app.route('/tito', methods=['POST'])
def tito():
  print("received: " + json.dumps(request.json), flush = True)

  # If bot is silenced, return.
  if silencedUntil and silencedUntil > time.time():
    return '200'

  # if mentioned by itself, Tito won't answer.
  if request.json['from']['firstName'] == 'Tito':
    return '200'

  time.sleep(1)

  anwser = getAnswer(request.json)
  post_response(anwser, request.json['workspaceId'], request.json['groupId'])

  return '200'

@app.route('/tito/newmember', methods=['POST'])
def tito_greet():
  print("received: " + json.dumps(request.json), flush = True)

  # If bot is silenced, return.
  if silencedUntil and silencedUntil > time.time():
    return '200'

  # if new member is itself, Tito won't answer.
  if request.json['member']['firstName'] == 'Tito':
    return '200'

  time.sleep(1)

  answer = ('Bienvenido ' + request.json['member']['firstName'] + '!\n'
            'Soy un bot, y estoy para ayudarte.\n' 
            'Envía @Tito help para ver los comandos a los que puedo responder.')
  post_response(answer, request.json['workspaceId'], request.json['groupId'])

  return '200'

@app.route('/robo/mention', methods=['POST'])
def robo_mention():
  roboLoginCredentials = {
    'email': 'titobot@hypechat.com',
    'password': 'titosPassword123!'
  }

  roboAuthToken = login(roboLoginCredentials)

  print("received: " + json.dumps(request.json), flush = True)
  time.sleep(1)

  url = baseUrl + '/workspaces/' + str(request.json['workspaceId']) + '/messages'
  payload = {
    'recipientId': None,
    'groupId': request.json['groupId'],
    'message': ('Hola ' + request.json['from']['firstName'] + '!\n')
  }

  r = requests.post(url, headers = { 'X-Auth': roboAuthToken }, json = payload)

  return '200'