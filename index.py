import time
from iqoptionapi.stable_api import IQ_Option

API = IQ_Option('mendes-gustavo@live.com', '6600653g')
API.connect()

API.change_balance('PRACTICE') #PRACTICE / REAL
#print('Tipo de conta: ', API.get_balance_mode())

if(API.check_connect() == False):
	print('Erro ao se conectar. Verifique se seu e-mail ou senha estão corretos.')

else:
	print('Conectado com sucesso')

time.sleep(1)


