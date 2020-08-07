import time, json
from iqoptionapi.stable_api import IQ_Option
from datetime import datetime

API = IQ_Option('email', 'password')
API.connect()

API.change_balance('PRACTICE') #PRACTICE / REAL
print('Tipo de conta: ', API.get_balance_mode())

if(API.check_connect() == False):
	print('Erro ao se conectar. Verifique se seu e-mail ou senha estão corretos.')

else:
	print('Conectado com sucesso')

time.sleep(1)

def perfil():
	perfil = json.loads(json.dumps(API.get_profile()))

	return perfil['result']

def timestamp_converter(x):
	hora = datetime.strptime(datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
	hora = hora.replace(tzinfo=tz.gettz('GMT'))
	
	return str(hora)[:-6]

x = perfil()

print(x['name'])
print(x['nickname'])
print(x['currency'])
print(API.get_balance())