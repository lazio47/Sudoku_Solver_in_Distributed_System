import errno
from itertools import product
import socket
import json
import threading
import time
from .sudoku import Sudoku
    
    
class Peer:
    def __init__(self, args):
        # rede
        self.host = '0.0.0.0'
        self.port = args.port_p2p
        self.peer_address = args.peer_address
        self.handicap = args.handicap
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = {}
        self.peers = set()
        self.connected_peers = {}
        self.peers_times = {}
        self.is_alive = True
        self.ocupado = False
        self.network = {}
        self.solver = Sudoku([])
        self.fulladdr = self.get_ip()

        # sudoku
        self.peers_disponiveis = []
        self._connections = {}
        self.por_resolver = 0
        self.indice_a_resolver = 0
        self.task_peer = {}
        self.tasks = []
        self.my_validations = 0
        self.all_validations = 0
        me = self.fulladdr+":"+str(self.port)
        self.all_peers_validations = {me:0}
        self.solved = 0
        self.tarefa_actual = 2
        self.novas_possible_solutions = []

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"Peer listening on {self.fulladdr}:{self.port}")
        threading.Thread(target=self.accept_connections).start()
        threading.Thread(target=self.alive).start()
        threading.Thread(target=self.are_peers_alive).start()
        if self.peer_address != None:
            peer_host = self.peer_address.split(":")[0]
            peer_port = int(self.peer_address.split(":")[1])
            self.connect_to_peer(peer_host, peer_port)


    def accept_connections(self):
        while True:
            conn, addr = self.sock.accept()
            if len(self.peers) >= len(self.connections):
                print(f"Connection established with {addr}")
                self.connections[str(addr[0])+":"+str(addr[1])] = conn
                self.peers_disponiveis.append(conn)
                threading.Thread(target=self.handle_client, args=(conn,)).start()
                self.send_connected_peers(conn)

    def send_connected_peers(self, conn):
        conn_info = {"command": "peers_info", "peers": list(self.peers), "validations": self.all_validations, "solved": self.solved}
        json_message = json.dumps(conn_info).encode()
        size = len(json_message).to_bytes(8, 'big')
        conn.sendall(size+json_message)

    def handle_client(self, conn):
        while True:
            try:
                size_bytes = conn.recv(8)
                size = int.from_bytes(size_bytes, byteorder='big')
                data = conn.recv(size).decode()
                if not data:
                    print("Client disconnected")
                    break
                json_msg = json.loads(data)
                self.read_msg(json_msg, conn)
            except ConnectionResetError:
                print("Client forcibly disconnected")
                conn.close()
                break

    def connect_to_peer(self, host, port):
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if (host, port) not in self.peers:
            peer_socket.connect((host, port))
            self.peers.add((host,port))
            threading.Thread(target=self.handle_peer, args=(peer_socket,)).start()

    def handle_peer(self, peer_socket):
        while True:
            try:
                size_bytes = peer_socket.recv(8)
                size = int.from_bytes(size_bytes, byteorder='big')

                total_bytes_to_receive = size
                buffer_size = 4096 

                data_received = b''
                while total_bytes_to_receive > 0:
                    chunk_size = min(buffer_size, total_bytes_to_receive)
                    chunk = peer_socket.recv(chunk_size)
                    if not chunk:
                        break 
                    data_received += chunk
                    total_bytes_to_receive -= len(chunk)

                data = data_received.decode()
                if not data:
                    peer_socket.close()
                    break
                json_msg = json.loads(data)
                threading.Thread(target=self.read_msg, args=(json_msg, peer_socket,)).start()
            except ConnectionResetError:
                peer_socket.close()
                break

    def send_to_peers(self, message):    
        json_msg = json.dumps(message).encode()
        size = len(json_msg).to_bytes(8, 'big')
        for peer_name, peer_socket in list(self.connections.items()):
            try:
                peer_socket.sendall(size+json_msg)
            except OSError as e:
                if e.errno!= errno.EPIPE:
                    raise
                print("Socket closed unexpectedly")
                for key, value in list(self.connections.items()):
                    if value == peer_socket:
                        break

    def send_to_peer(self, peer_socket, message):
        json_msg = json.dumps(message).encode()
        size = len(json_msg).to_bytes(8, 'big')
        try:
            peer_socket.sendall(size+json_msg)
        except OSError as e:
            if e.errno!= errno.EPIPE:
                raise
            print("Socket closed unexpectedly")
            for key, value in list(self.connections):
                if value == peer_socket:
                    break
    
    def read_msg(self, json_msg, peer_socket):
        if json_msg["command"] == "message":
            msg = json_msg["message"]
            print(f"Received message from peer: {msg}")

        elif json_msg["command"] == "peers_info":
            self.all_validations = json_msg["validations"]
            self.solved = json_msg["solved"]
            for host, port in json_msg["peers"]:
                if (host, port) not in self.peers and (host, port) != (self.fulladdr, self.port):
                    self.connect_to_peer(host, port)

            conn_ack = {"command": "peers_ack", "peers": list(self.peers)+[(self.fulladdr, self.port)], "my_socket": peer_socket.getsockname(), "host_port": (self.get_ip(), self.port)}
            json_message = json.dumps(conn_ack).encode()
            size = len(json_message).to_bytes(8, 'big')
            peer_socket.sendall(size+json_message)

        elif json_msg["command"] == "peers_ack":
            self.connected_peers[json_msg["host_port"][0]+":"+str(json_msg["host_port"][1])] = json_msg["my_socket"]
            for host, port in json_msg["peers"]:
                if (host, port) not in self.peers and (host, port) != (self.fulladdr, self.port):
                    self.connect_to_peer(host, port)

        elif json_msg["command"] == "ack":
            peer = json_msg["peer"]
            self.peers_times[peer[0]+":"+str(peer[1])] = int(time.time())
            self.network[peer[0]+":"+str(peer[1])] = json_msg["network"]
            self.all_peers_validations[peer[0]+":"+str(peer[1])] = json_msg["validations"]

        elif json_msg["command"] == "solved":
            self.solved += 1

        elif json_msg["command"] == "validations":
            self.all_validations = json_msg["validations"]

        elif json_msg["command"] == "task":
            if json_msg["tipo"] == 2:
                linhas = json_msg["task"]
                combinacoes = self.combinar_2_linhas(linhas[0], linhas[1])
                message = {"command": "task_resp", "tipo": 2, "indice": json_msg["indice"], "combinacao": combinacoes, "validations": self.solver.validation}
                self.my_validations += self.solver.validation
                self.solver.validation = 0
            else:
                linhas = json_msg["task"]
                combinacoes = self.combinar_3_linhas(linhas[0], linhas[1], linhas[2])
                self.my_validations += self.solver.validation
                message = {"command": "task_resp", "tipo": 3, "indice": json_msg["indice"], "combinacao": combinacoes, "validations": self.solver.validation}
                self.solver.validation = 0
            self.send_to_peer(peer_socket, message)

        elif json_msg["command"] == "task_resp":
            indice = json_msg["indice"]
            combinacoes = json_msg["combinacao"]
            self.all_validations += json_msg["validations"]
            del self.task_peer[indice]
            print(f"Combinacoes do peer {peer_socket.getpeername()} <<>>[ {indice}]: {combinacoes}\n")
            if json_msg["tipo"] == 2:
                for combinacao in combinacoes:
                    if combinacao[0] not in self.novas_possible_solutions[2*indice]:
                        self.novas_possible_solutions[2*indice].append(combinacao[0])
                    if combinacao[1] not in self.novas_possible_solutions[2*indice+1]:
                        self.novas_possible_solutions[2*indice+1].append(combinacao[1])
            elif json_msg["tipo"] == 3:
                for combinacao in combinacoes:
                    if combinacao[0] not in self.novas_possible_solutions[3*indice]:
                        self.novas_possible_solutions[3*indice].append(combinacao[0])
                    if combinacao[1] not in self.novas_possible_solutions[3*indice+1]:
                        self.novas_possible_solutions[3*indice+1].append(combinacao[1])
                    if combinacao[2] not in self.novas_possible_solutions[3*indice+2]:
                        self.novas_possible_solutions[3*indice+2].append(combinacao[2])
            self.por_resolver -= 1
            self.peers_disponiveis.append(peer_socket)


    def alive(self):
        while self.is_alive:
            ack_message = {"command": "ack", "peer": (self.fulladdr, self.port), "network": [f"{ip}:{porta}" for ip, porta in self.peers], "validations": self.my_validations}
            threading.Thread(target=self.send_to_peers, args=(ack_message,)).start()
            time.sleep(1)

    def are_peers_alive(self):
        while True:
            for peer_name, peer_socket in list(self.connections.items()):
                host, port = peer_name.split(':')[0], int(peer_name.split(':')[1])
                key = None
                peers_conn = list(self.connected_peers.items())
                for chave, valor in peers_conn:
                    if valor == [host, port]:
                        key = chave
                if key == None:
                    continue
                peer_host, peer_port = key.split(":")[0], int(key.split(":")[1])
                peer_socket_val = peer_host+":"+str(peer_port)
                if peer_socket_val in self.peers_times:
                    if int(time.time()) - self.peers_times[peer_socket_val] > 3:
                        print(f"Peer {(peer_host, peer_port)} desconnected!")
                        self.connections.pop(peer_name)
                        if(peer_socket in self.peers_disponiveis):
                            self.peers_disponiveis.remove(peer_socket)
                        self.peers.remove((peer_host, peer_port))
                        self.network.pop(peer_socket_val)
                        peer = self.connected_peers.pop(peer_socket_val, None)
                        self.peers_times.pop(peer_socket_val, None)
                        peer_socket.close()
                        peer = tuple(peer)
                        if peer in self.task_peer.values():
                            indice = None
                            for chave, valor in self.task_peer.items():
                                if valor == peer:
                                    indice = chave
                                    break 
                            self.task_peer.pop(indice)
                            print("A recuperar tarefa ", indice)
                            threading.Thread(target=self.oferecer_tarefa_especifica, args=(indice,)).start()
                        break

    def solve_sudoku(self, sudoku) -> list:
        time_inicial = int(time.time())
        self.solver = Sudoku(sudoku, handicap=self.handicap)
        possible_solutions = []
        for row_index in range(9):
            possible_solutions.append(self.solver.get_possible_solutions_for_row(row_index))

        self.tasks = {
                        0: possible_solutions[:2], 
                        1: possible_solutions[2:4],
                        2: possible_solutions[4:6],
                        3: possible_solutions[6:8]
        }
        self.novas_possible_solutions = [ [], [], [], [], [], [], [], [], possible_solutions[8]]
        self.por_resolver = 4
        self.indice_a_resolver = 0
        self.dividir_tarefas(2)

        print("Terminada a simplificacao 2 a 2!")
        self.tarefa_actual = 3


        self.por_resolver = 3
        self.indice_a_resolver = 0
        self.tasks = {
                        0: self.novas_possible_solutions[:3],
                        1: self.novas_possible_solutions[3:6],
                        2: self.novas_possible_solutions[6:9]
        }
        self.novas_possible_solutions = [[], [], [], [], [], [], [], [], []]
        self.dividir_tarefas(3)

        print("Terminada a simplificacao 3 a 3!")
        self.tarefa_actual = 2

        permutacoes = list(product(*self.novas_possible_solutions))

        for i, permutacao in enumerate(permutacoes):
            self.solver.set_solution(list(permutacao))
            if self.solver.check():
                print("Solucao encontrada:")
                self.solved += 1
                message = {"command": "solved"}
                self.send_to_peers(message)
                print(self.solver)
                break
        self.my_validations += self.solver.validation
        self.all_validations += self.solver.validation
        self.solver.validation = 0
        print("Tempo total: ", int(time.time()) - time_inicial, "s")

        message = {"command": "validations", "validations": self.all_validations}
        self.send_to_peers(message)
        return self.solver.solution
        
    def oferecer_tarefa_especifica(self, indice):
        while True:
            if self.peers_disponiveis != [] and self.indice_a_resolver <= len(self.tasks) - 1:
                for peer in self.peers_disponiveis:
                    message = {"command": "task", "tipo": self.tarefa_actual, "indice": self.indice_a_resolver, "task": self.tasks[self.indice_a_resolver]}
                    self.send_to_peer(peer, message)
                    self.task_peer[self.indice_a_resolver] = peer.getpeername()
                    self.indice_a_resolver += 1
                    self.peers_disponiveis.remove(peer)
                    return None
            elif not self.ocupado:
                threading.Thread(target=self.my_work, args=(indice, self.tarefa_actual,)).start()
                self.indice_a_resolver += 1
                return None

    def dividir_tarefas(self, tipo):
        while self.por_resolver > 0:
            if self.peers_disponiveis != [] and self.indice_a_resolver <= len(self.tasks) - 1:
                for peer in self.peers_disponiveis:
                    message = {"command": "task", "tipo": tipo, "indice": self.indice_a_resolver, "task": self.tasks[self.indice_a_resolver]}
                    self.send_to_peer(peer, message)
                    self.task_peer[self.indice_a_resolver] = peer.getpeername()
                    self.indice_a_resolver += 1
                    self.peers_disponiveis.remove(peer)
                    break
            else:
                if self.indice_a_resolver > len(self.tasks) - 1:
                    time.sleep(1)
                    continue
                else:
                    if not self.ocupado:
                        threading.Thread(target=self.my_work, args=(self.indice_a_resolver, tipo,)).start()
                        self.indice_a_resolver += 1

    def my_work(self, indice, tipo):
        self.ocupado = True
        if tipo == 2:
            combinacoes = self.combinar_2_linhas(self.tasks[indice][0], self.tasks[indice][1])
            for combinacao in combinacoes:
                if combinacao[0] not in self.novas_possible_solutions[2*indice]:
                    self.novas_possible_solutions[2*indice].append(combinacao[0])
                if combinacao[1] not in self.novas_possible_solutions[2*indice+1]:
                    self.novas_possible_solutions[2*indice+1].append(combinacao[1])
        else:
            combinacoes = self.combinar_3_linhas(self.tasks[indice][0], self.tasks[indice][1], self.tasks[indice][2])
            for combinacao in combinacoes:
                if combinacao[0] not in self.novas_possible_solutions[3*indice]:
                    self.novas_possible_solutions[3*indice].append(combinacao[0])
                if combinacao[1] not in self.novas_possible_solutions[3*indice+1]:
                    self.novas_possible_solutions[3*indice+1].append(combinacao[1])
                if combinacao[2] not in self.novas_possible_solutions[3*indice+2]:
                    self.novas_possible_solutions[3*indice+2].append(combinacao[2])
        self.my_validations += self.solver.validation
        self.all_validations += self.solver.validation
        self.solver.validation = 0
        print(f"Minhas coombinacoes [{indice}]: {combinacoes}")
        self.por_resolver -= 1
        self.ocupado = False

    def validar_2_combinacao(self, combinacao):
        self.solver._limit_calls()
        for coluna in range(9):
            numeros_na_coluna = [linha[coluna] for linha in combinacao]
            if len(numeros_na_coluna) != len(set(numeros_na_coluna)):
                return False
        return True

    def combinar_2_linhas(self, possiveis_solucoes_linha1, possiveis_solucoes_linha2):
        combinacoes_validas = []
        for solucao_linha1 in possiveis_solucoes_linha1:
            for solucao_linha2 in possiveis_solucoes_linha2:
                combinacao = [solucao_linha1, solucao_linha2]
                if self.validar_2_combinacao(combinacao):
                    combinacoes_validas.append(combinacao)
        tuplas_sem_duplicatas = set(tuple(tuple(subsublista) for subsublista in sublista) for sublista in combinacoes_validas)
        lista_sem_duplicadas = [list(list(subsublista) for subsublista in sublista) for sublista in tuplas_sem_duplicatas]
        print("validations: ", self.solver.validation)
        return lista_sem_duplicadas
    
    def validar_3_combinacao(self, combinacao):
        # Verifica se não há números repetidos em cada coluna
        self.solver._limit_calls()
        for coluna in range(9):
            numeros_na_coluna = [linha[coluna] for linha in combinacao]
            if len(numeros_na_coluna) != len(set(numeros_na_coluna)):
                return False

        for i in range(0, 3, 3):
            for j in range(0, 3, 3):
                numeros_no_quadrante = []
                for k in range(3):
                    for l in range(3):
                        numeros_no_quadrante.append(combinacao[i + k][j + l])
                if len(numeros_no_quadrante) != len(set(numeros_no_quadrante)):
                    return False
        
        return True

    def combinar_3_linhas(self, possiveis_solucoes_linha1, possiveis_solucoes_linha2, possiveis_solucoes_linha3):
        # Combina as possíveis soluções das três linhas
        combinacoes_validas = []
        for solucao_linha1 in possiveis_solucoes_linha1:
            for solucao_linha2 in possiveis_solucoes_linha2:
                for solucao_linha3 in possiveis_solucoes_linha3:
                    combinacao = [solucao_linha1, solucao_linha2, solucao_linha3]
                    if self.validar_3_combinacao(combinacao):
                        combinacoes_validas.append(combinacao)
        tuplas_sem_duplicatas = set(tuple(tuple(subsublista) for subsublista in sublista) for sublista in combinacoes_validas)
        lista_sem_duplicadas = [list(list(subsublista) for subsublista in sublista) for sublista in tuplas_sem_duplicatas]
        print("validations: ", self.solver.validation)
        return lista_sem_duplicadas


    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address