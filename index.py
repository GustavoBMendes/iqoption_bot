import time, json, sys, logging
from iqoptionapi.stable_api import IQ_Option
from datetime import datetime
from dateutil import tz
import PySimpleGUI as sg

sg.theme('DarkAmber') 


#desabilitar mensagens de erro
#logging.disable(level=(logging.ERROR))


def login(self):
	API = IQ_Option(self.values[0], self.values[1])
	
	API.connect()

	

	#API.change_balance('PRACTICE') #PRACTICE / REAL
	#print('Tipo de conta: ', API.get_balance_mode())

	if(API.check_connect() == False):
		print(f'Erro ao se conectar. Verifique se seu e-mail ou senha estão corretos.')

	else:
		print(f'Conectado com sucesso')
		#paridades(API)
		self.janela.close()
		entradas = TelaEntradas(API)

	return API

def perfil(API):
	perfil = json.loads(json.dumps(API.get_profile()))

	return perfil['result']

def timestamp_converter(x):
	hora = datetime.strptime(datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
	hora = hora.replace(tzinfo=tz.gettz('GMT'))
	
	return str(hora.astimezone(tz.gettz('America/Sao Paulo')))[:-6]

def banca(API):
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

def payout(API, par, tipo, timeframe = 1): #tipo = DIGITAL/BINARY; timeframe = tempo de expiração da vela
	
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

def paridades(API):
	par = API.get_all_open_time()

	for paridade in par['binary']:
		
		if par['binary'][paridade]['open'] == True:
			print('[ BINARY ]: ' + paridade + ' | Payout: ' + str(payout(API, paridade, 'binary')))

	print('\n')

	for paridade in par['digital']:
		
		if par['digital'][paridade]['open'] == True:
			print('[ DIGITAL ]: ' + paridade + ' | Payout: ' + str(payout(API, paridade, 'digital')))

def historico():
	status,historico = API.get_position_history_v2('turbo-option', 7, 0, 0, 0)

	''' exibir dados em formato json
	for x in historico['positions']:
		print(json.dumps(x, indent=1))
	'''
	'''
		:::::::::::::::: [ MODO DIGITAL ] ::::::::::::::::
	FINAL OPERACAO : historico['positions']['close_time']
	INICIO OPERACAO: historico['positions']['open_time']
	LUCRO          : historico['positions']['close_profit']
	ENTRADA        : historico['positions']['invest']
	PARIDADE       : historico['positions']['raw_event']['instrument_underlying']
	DIRECAO        : historico['positions']['raw_event']['instrument_dir']
	VALOR          : historico['positions']['raw_event']['buy_amount']

	:::::::::::::::: [ MODO BINARIO ] ::::::::::::::::
	MODO TURBO tem as chaves do dict diferentes para a direção da operação(put ou call) 
		e para exibir a paridade, deve ser utilizado:
	DIRECAO : historico['positions']['raw_event']['direction']
	PARIDADE: historico['positions']['raw_event']['active']
	'''

	for x in historico['positions']:
		print('PAR: '+str(x['raw_event']['active'])+' /  DIRECAO: '+str(x['raw_event']['direction'])+' / VALOR: '+str(x['invest']))
		print('LUCRO: '+str(x['close_profit'] if x['close_profit'] == 0 else round(x['close_profit']-x['invest'], 2) ) + ' | INICIO OP: '+str(timestamp_converter(x['open_time'] / 1000))+' / FIM OP: '+str(timestamp_converter(x['close_time'] / 1000)))
		print('\n')

def fazer_entrada(API, valor, par, tipo, timeframe):
	#timeframe = tempo em min, valor = valor da entrada, par = moedas tipo 'EURUSD', tipo = put ou call

	#digital
	_,id = API.buy_digital_spot(par, valor, tipo, timeframe)
	if isinstance(id, int):
		while True:
			status, lucro =  API.check_win_digital_v2(id)

			if status:
				if lucro > 0:
					print('RESULTADO: WIN / LUCRO = ' + str(round(lucro, 2)))
				else:
					print('RESULTADO: LOSS / LUCRO = -' + str(valor))
				break

	#binaria
	status, id = API.buy(valor, par, tipo, timeframe)

	if status:
		resultado, lucro = API.check_win_v4(id)
		print('RESULTADO: ' + resultado + ' / LUCRO = ' + str(round(lucro, 2)))


def TelaEntradas(api):
		
	''' COMPARAÇÃO HORARIO
	if datetime.now().strftime('%d-%m-%Y %H:%M') == 'horario aqui no mesmo formato':
		print('mesma hora')
	'''

	x = perfil(api)
	layout2 = [
		[sg.Text('Bem-vindo '), sg.Text(x['name'])],
		[sg.Text('Banca Inicial: '), sg.Text(banca(api))],
		[sg.Text('Horário atual: '), sg.Text(datetime.now().strftime('%d-%m-%Y %H:%M:%S'), key='DATA')],
		[sg.Text('Lista de entradas: '), sg.Input()],
		[sg.Button('Iniciar Robô'), sg.Button('Cancelar entradas')], #ao cancelar entradas o programa é fechado
	]
	janela2 = sg.Window('Tela de login na IQ Option').layout(layout2)
	inicio = 0
	lista = []

	while True:
		event, values = janela2.Read(timeout=10)

		if event in (None, 'Cancelar entradas', sg.WIN_CLOSED):
			break

		if event == 'Iniciar Robô':
			if inicio == 0:
				lista = ['11:06:00', '11:07:00']
				inicio = 1

		if inicio == 1:
			for hora in lista:
				if hora == datetime.now().strftime('%H:%M:%S'):
					print('Fez entrada')
					fazer_entrada(api, 2, 'CADCHF', 'call', 2)

		janela2.FindElement('DATA').Update(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
		#time.sleep(1)

class TelaLogin:
	def __init__(self):
		
		layout=[
			[sg.Text('E-mail: '), sg.Input()],
			[sg.Text('Senha: '), sg.Input(password_char=('*'))],
			[sg.Button('Login')],
			[sg.Output(size=(50,15))],
		]

		self.janela = sg.Window('Tela de login na IQ Option').layout(layout)

	def Iniciar(self):
		while True:
			self.button, self.values = self.janela.Read()
			print(f'Por favor, aguarde.')
			API = login(self)
			print(f'{self.values[0]}')
			print(f'{self.values[1]}')


#fazer_entrada(2, 'AUDJPY', 'call', 1)

tela = TelaLogin()
tela.Iniciar()
