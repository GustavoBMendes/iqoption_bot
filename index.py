import time, json
from iqoptionapi.stable_api import IQ_Option
from datetime import datetime
from dateutil import tz
import PySimpleGUI as sg

API = IQ_Option('email', 'password')
API.connect()

API.change_balance('PRACTICE') #PRACTICE / REAL
print('Tipo de conta: ', API.get_balance_mode())

if(API.check_connect() == False):
	print('Erro ao se conectar. Verifique se seu e-mail ou senha estão corretos.')

else:
	print('Conectado com sucesso')


def perfil():
	perfil = json.loads(json.dumps(API.get_profile()))

	return perfil['result']

def timestamp_converter(x):
	hora = datetime.strptime(datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
	hora = hora.replace(tzinfo=tz.gettz('GMT'))
	
	return str(hora.astimezone(tz.gettz('America/Sao Paulo')))[:-6]

def banca():
	return API.get_balance()

def capturarVelas(par, tempo_vela, num_velas): #tempo em segundos
	hora = time.time()
	if(num_velas <= 1000):
		velas = API.get_candles(par, tempo_vela, num_velas, hora)
		for vela in velas:
			print('Horário de início: ' + str(timestamp_converter(vela['from'])) + ' valor de abertura: ' + str(vela['open']))

	else:
		total = []
		if(num_velas <= 9999):
			for i in range( int(round((num_velas/1000), 0)) ):
				X = API.get_candles(par, tempo_vela, 1000, hora)
				total = X + total
				hora = int(X[0]['from']) - 1
			
			for velas in total:
				print(timestamp_converter(velas['from']))
		else:
			print('Número de velas igual ou superior a 10000! Entre com um valor menor.')

def capturarVelas_realTime(par, tempo_vela):

	API.start_candles_stream(par, tempo_vela, 1)
	time.sleep(1)

	while True:
		vela = API.get_realtime_candles(par, tempo_vela)
		for valores in vela:
			print(vela[valores]['close'])
		time.sleep(1)
	API.stop_candles_stream(par, tempo_vela)

def payout(par, tipo, timeframe = 1): #tipo = DIGITAL/BINARY; timeframe = tempo de expiração da vela
	
	if tipo == 'binary':
		a = API.get_all_profit()
		return int(100 * a[par]['binary'])

	elif tipo == 'digital':
		try:
			API.subscribe_strike_list(par, timeframe)
			while True:
				d = API.get_digital_current_profit(par, timeframe)
				if d != False:
					d = int(d)
					break
				time.sleep(1)
			API.unsubscribe_strike_list(par, timeframe)
			return d

		except:
			print('Ativo não existe')
			return False

class TelaPython:
	def __init__(self):

		layout=[
			[sg.Text('Nome'), sg.Input()],
			[sg.Text(banca()), sg.Input()],
			[sg.Button('Enviar')]
		]

		janela=sg.Window('Dados do usuário').layout(layout)

		self.button, self.values = janela.Read()

	def Iniciar(self):
		print(self.values)

'''
par = API.get_all_open_time()

for paridade in par['binary']:
	
	if par['binary'][paridade]['open'] == True:
		print('[ BINARY ]: ' + paridade + ' | Payout: ' + str(payout(paridade, 'binary')))

print('\n')

for paridade in par['digital']:
	
	if par['digital'][paridade]['open'] == True:
		print('[ DIGITAL ]: ' + paridade + ' | Payout: ' + str(payout(paridade, 'digital')))
'''
tela = TelaPython()
tela.Iniciar()
