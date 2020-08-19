import time, json, sys, logging, threading
from iqoptionapi.stable_api import IQ_Option
from datetime import datetime
from datetime import timedelta
from dateutil import tz
import PySimpleGUI as sg

sg.theme('DarkAmber') 

#desabilitar mensagens de erro
#logging.disable(level=(logging.ERROR))

lucro_total = 0

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
		TelaEntradas(API, self.values[0], self.values[1])

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

def payout(API, par, tipo, timeframe): #tipo = DIGITAL/BINARY; timeframe = tempo de expiração da vela
	
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

def martingale(valor, payout, perca):
	lucro_esperado = valor * payout

	while True:
		if round(valor * payout, 2) > round(abs(perca) + lucro_esperado, 2):
			return round(valor, 2)
		valor += 0.05

def fazer_entrada(valor, par, tipo, timeframe, hora, email, senha, mgales):
	#timeframe = tempo em min, valor = valor da entrada, par = moedas tipo 'EURUSD', tipo = put ou call

	#digital
	
	API = IQ_Option(email, senha)
	API.connect()

	global lucro_total

	_,id = API.buy_digital_spot(par, valor, tipo, timeframe)
	
	if isinstance(id, int):
		print('Fez entrada -> Hora: ' + hora + ', Moeda: ' + par + ', Direção: ' + tipo + '\n')
		while True:
			status, lucro = API.check_win_digital_v2(id)

			if status:
				if lucro > 0:
					print('Operação das '+ hora + ' na moeda ' + par + '\n RESULTADO: WIN / LUCRO = ' + str(round(lucro, 2)) + '\n')
					lucro_total += lucro
					
				else:
					perca = valor
					print('Operação das '+ hora + ' na moeda ' + par + '\n RESULTADO: LOSS / LUCRO = -' + str(perca) + '\n')
					lucro_total -= valor
					if int(mgales) > 0:
						Payout = payout(API, par, 'digital', timeframe) / 100
						valor = martingale(valor, Payout, perca)
						print('Entrando com martingale para a operação das '+ hora + ' na moeda ' + par)
						int(mgales) -= 1
						fazer_entrada(valor, par, tipo, timeframe, hora, email, senha, mgales)
						return

				print('LUCRO TOTAL: ' + str(lucro_total) + '\n')
				return


	#binaria
	status, id = API.buy(valor, par, tipo, timeframe)
	
	if status:
		print('Fez entrada -> Hora: ' + hora + ', Moeda: ' + par + ', Direção: ' + tipo)
		resultado, lucro = API.check_win_v4(id)
		if lucro > 0:
			print('Operação das '+ hora + ' na moeda ' + par + '\n RESULTADO: WIN / LUCRO = ' + str(round(lucro, 2)) + '\n')
			lucro_total += lucro
			lucro = 0
		else:
			print('Operação das '+ hora + ' na moeda ' + par + '\n RESULTADO: LOSS / LUCRO = -' + str(valor) + '\n')
			lucro_total -= valor
			lucro = 0
		print('LUCRO TOTAL: ' + str(lucro_total) + '\n')
		return

	print('Ativo não disponível no modo digital e binário')
	

def carregar_sinais():
	arquivo = open('sinais.txt', encoding='UTF-8')
	lista = arquivo.read()
	arquivo.close
	
	lista = lista.split('\n')
	
	for index,a in enumerate(lista):
		if a == '':
			del lista[index]

	return lista

def modo_stopLoss(api, janela2, inicio, lista, em_andamento, stop_loss, email, senha):
	print('ATENÇÃO!\nModo stop win DESATIVADO! \nModo stop loss ATIVADO!\n')
	global lucro_total

	while True:
		event, values = janela2.Read(timeout=10)

		if event in (None, sg.WIN_CLOSED):
			break

		if event in ('Encerrar entradas'):
			print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
			break

		for sinal in lista:
			dados = sinal.split(',')
			if dados[0] == datetime.now().strftime('%H:%M:%S'):

				if lucro_total > -(stop_loss):
					#em_andamento.append(dados[0])
					lista.remove(sinal)
					threading.Thread(target=fazer_entrada, args=(2, dados[1], dados[2], 1, dados[0], email, senha, )).start()

				else:
					print('Stop loss atingido.')
					print('A entrada da hora: ' + dados[0] + ', Moeda: ' + dados[1] + ', Direção: ' + dados[2] + ' não foi feita.')
					print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
					return
				
				if len(lista) == 0:
					print('A lista chegou ao fim!')
					print('Para finalizar, clique no botão Encerrar entradas')
					print('Você ainda pode alterar o arquivo sinais.txt e após isso importar mais uma lista clicando no botão Iniciar robô\n')	

		janela2.FindElement('DATA').Update(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))

		#time.sleep(1)

def modo_stopWin(api, janela2, inicio, lista, em_andamento, stop_win, email, senha, mgales):
	print('ATENÇÃO!\nModo stop win ATIVADO! \nModo stop loss DESATIVADO!')
	print('Seu stop win é de: ', stop_win)
	print('O robo está configurada para entrar com até ' + mgales + ' gales\n')
	global lucro_total

	while True:
		event, values = janela2.Read(timeout=10)

		if event in (None, sg.WIN_CLOSED):
			break

		if event in ('Encerrar entradas'):
			print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
			break

		for sinal in lista:
			dados = sinal.split(',')
			d = datetime.strptime(dados[0], '%H:%M:%S') + timedelta(seconds=-5)

			if d.strftime('%H:%M:%S') == datetime.now().strftime('%H:%M:%S'):

				if lucro_total < stop_win:
					#em_andamento.append(dados[0])
					lista.remove(sinal)
					threading.Thread(target=fazer_entrada, args=(2, dados[1], dados[2], 1, dados[0], email, senha, mgales, )).start()

				else:
					print('Stop win atingido.')
					print('A entrada da hora: ' + dados[0] + ', Moeda: ' + dados[1] + ', Direção: ' + dados[2] + ' não foi feita.')
					print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
					return
				
				if len(lista) == 0:
					print('A lista chegou ao fim!')
					print('Para finalizar, clique no botão Encerrar entradas')
					print('Você ainda pode alterar o arquivo sinais.txt e após isso importar mais uma lista clicando no botão Iniciar robô\n')	

		janela2.FindElement('DATA').Update(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))

		#time.sleep(1)

def modo_stopWin_stopLoss(janela2, inicio, lista, em_andamento, stop_loss, stop_win, email, senha):

	print('ATENÇÃO!\nModo stop win ATIVADO! \nModo stop loss ATIVADO!\n')
	global lucro_total

	while True:
		event, values = janela2.Read(timeout=10)

		if event in (None, sg.WIN_CLOSED):
			break

		if event in ('Encerrar entradas'):
			print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
			break

		for sinal in lista:
			dados = sinal.split(',')
			if dados[0] == datetime.now().strftime('%H:%M:%S'):

				if lucro_total > -(stop_loss) and lucro_total < stop_win:
					#em_andamento.append(dados[0])
					lista.remove(sinal)
					threading.Thread(target=fazer_entrada, args=(2, dados[1], dados[2], 1, dados[0], email, senha, )).start()

				else:
					print('Stop win ou stop loss atingido.')
					print('A entrada da hora: ' + dados[0] + ', Moeda: ' + dados[1] + ', Direção: ' + dados[2] + ' não foi feita.')
					print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
					return
				
				if len(lista) == 0:
					print('A lista chegou ao fim!')
					print('Para finalizar, clique no botão Encerrar entradas')
					print('Você ainda pode alterar o arquivo sinais.txt e após isso importar mais uma lista clicando no botão Iniciar robô\n')	

		janela2.FindElement('DATA').Update(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))

		#time.sleep(1)

def modo_semStops(janela2, inicio, lista, em_andamento, email, senha):
	print('ATENÇÃO!\nModo stop win DESATIVADO! \nModo stop loss DESATIVADO!\n')
	global lucro_total

	while True:
		event, values = janela2.Read(timeout=10)

		if event in (None, sg.WIN_CLOSED):
			break

		if event in ('Encerrar entradas'):
			print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
			break

		for sinal in lista:
			dados = sinal.split(',')
			if dados[0] == datetime.now().strftime('%H:%M:%S'):

				#em_andamento.append(dados[0])
				lista.remove(sinal)
				threading.Thread(target=fazer_entrada, args=(2, dados[1], dados[2], 1, dados[0], email, senha, )).start()

				if len(lista) == 0:
					print('A lista chegou ao fim!')
					print('Para finalizar, clique no botão Encerrar entradas')
					print('Você ainda pode alterar o arquivo sinais.txt e após isso importar mais uma lista clicando no botão Iniciar robô\n')	

		janela2.FindElement('DATA').Update(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))

		#time.sleep(1)

def TelaEntradas(api, email, senha):
	
	x = perfil(api)
	layout2 = [
		[sg.Text('Bem-vindo '), sg.Text(x['name'])],
		[sg.Text('Banca Inicial: '), sg.Text(banca(api), key='BANCA')],
		[sg.Text('Horário atual: '), sg.Text(datetime.now().strftime('%d-%m-%Y %H:%M:%S'), key='DATA')],
		[sg.Text('Tipo de conta selecionada: '), sg.Text(api.get_balance_mode(), key='CONTA')],
		[sg.Radio('Conta real', "RADIO1", key='CR', enable_events=True, default=True), sg.Radio('Conta de treinamento', "RADIO1", key='CT', enable_events=True)],
		[sg.Text('_'*115, text_color='white')],

		[sg.Text('ATENÇÃO:', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('Para importar os sinais, é necessário configurar o arquivo "sinais.txt" ', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('Este arquivo se encontra na mesma pasta de inicialização do robô.', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('Ele deve ser configurado da seguinte forma: ', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('Um sinal em cada linha do arquivo, as informações devem estar separadas por vírgula "," e não podem conter espaço entre elas.', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('As informações devem ser escritas da seguinte forma e na seguinte ordem: ', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('Horário,par de moedas,call ou put,tempo de expiração', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('Exemplo: ', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('12:16:00,EURUSD,call,1', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('O arquivo "exemplo.txt" demonstra exatamente como a lista deve ser configurada.', text_color=sg.theme_element_background_color(), background_color=sg.theme_text_color())],
		[sg.Text('_'*115, text_color='white')],

		[sg.Text('Inserir o valor de Stop win/loss nos proximos 2 campos, caso queira desabilitar essas funções, deixe o valor como 0 (zero).')],
		[sg.Text('O robô pode ser configurado para trabalhar em 4 modos: Com stop win e stop loss, apenas stop win, apenas stop loss, ou sem os dois stops.')],
		[sg.Text('Stop Win: ')],
		[sg.Input('0')],
		[sg.Text('Stop Loss: ')],
		[sg.Input('0')],
		[sg.Text('_'*115, text_color='white')],

		[sg.Text('Valor das entradas: ')],
		[sg.Input('0')],
		[sg.Text('_'*115, text_color='white')],

		[sg.Text('Número de Martin Gales: ')],
		[sg.Input('0')],
		[sg.Button('Iniciar Robô'), sg.Button('Encerrar entradas')], #ao cancelar entradas o programa é fechado
		[sg.Output(size=(115,10))],
	]
	janela2 = sg.Window('Tela de Operações').layout(layout2)
	event, values = janela2.Read(timeout=10)

	if values['CR'] == True:
		api.change_balance('REAL')
		janela2.FindElement('CONTA').Update(api.get_balance_mode())

	inicio = 0
	stop_win = 0
	stop_loss = 0
	lista = dict()
	em_andamento = []
	msg_inicio = 0

	while True:
		event, values = janela2.Read(timeout=10)
		
		if event in (None, sg.WIN_CLOSED):
			break

		if event == 'CR':
			api.change_balance('REAL')
			janela2.FindElement('CONTA').Update(api.get_balance_mode())
			print('Conta real selecionada')

		if event == 'CT':
			api.change_balance('PRACTICE')
			janela2.FindElement('CONTA').Update(api.get_balance_mode())
			print('Conta de treinamento selecionada')

		if msg_inicio == 0:
			print('É aqui que o robô irá conversar com você!\n')
			msg_inicio = 1

		if event in ('Encerrar entradas'):
			print('Os sinais da lista foram cancelados! Agora você pode alterar sua lista de sinais e as configurações de stop win/loss.\n')
			inicio = 0
			lista = dict()
			em_andamento = []

		if event == 'Iniciar Robô':
			if inicio == 0:
				stop_win = float(values[0])
				stop_loss = float(values[1])
				mgales = values[3]

				lista = carregar_sinais()
				inicio = 1
				print('Lista de sinais carregada!')
				print('A partir de agora os sinais da lista e as configurações de stop win/loss, valor de entradas e martingale não podem ser alterados, caso queira alterá-los, clique no botão Cancelar Entradas.\n')

				if stop_loss > 0 and stop_win > 0:
					modo_stopWin_stopLoss(janela2, inicio, lista, em_andamento, stop_loss, stop_win, email, senha, mgales)
					inicio = 0
					lista = dict()
					em_andamento = []


				elif stop_loss > 0 and stop_win == 0:
					modo_stopLoss(api, janela2, inicio, lista, em_andamento, stop_loss, email, senha, mgales)
					inicio = 0
					lista = dict()
					em_andamento = []

				elif stop_loss == 0 and stop_win > 0:
					modo_stopWin(api, janela2, inicio, lista, em_andamento, stop_win, email, senha, mgales)
					inicio = 0
					lista = dict()
					em_andamento = []
				
				else:
					modo_semStops(janela2, inicio, lista, em_andamento, email, senha, mgales)
					inicio = 0
					lista = dict()
					em_andamento = []
		
		janela2.FindElement('DATA').Update(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
		#time.sleep(1)

class TelaLogin:
	def __init__(self):
		
		layout=[
			[sg.Text('E-mail: '), sg.Input()],
			[sg.Text('Senha: '), sg.Input(password_char=('*'))],
			[sg.Button('Login')],
			[sg.Output(size=(50,5))],
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
