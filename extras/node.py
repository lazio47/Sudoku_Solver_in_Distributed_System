import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from Peer import Peer
import argparse


class SudokuHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/stats':
                stats = self.get_stats()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(stats, indent=4).encode())

            elif self.path == '/network':
                network_info = self.get_network_info()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(network_info, indent=4).encode())

            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({'error': str(e)})
            self.wfile.write(response.encode('utf-8'))

    def do_POST(self):
        if self.path == '/solve':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            puzzle = data.get('sudoku')

            if not puzzle:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Sudoku não fornecido"}).encode())
            else:
                solved_puzzle = node.solve_sudoku(puzzle)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(solved_puzzle).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def get_stats(self):
        me = node.fulladdr+":"+str(node.port)
        node.all_peers_validations[me] = node.my_validations
        all = node.all_peers_validations
        nodes = [
            {"address": endereco, "validations": validacoes} 
            for endereco, validacoes in all.items()
            if (endereco.split(":")[0], int(endereco.split(":")[1])) in node.peers
            or (endereco.split(":")[0], int(endereco.split(":")[1])) == (node.fulladdr, node.port)
        ]
        stats = {
                "all": {
                        "solved": node.solved,
                        "validations": node.all_validations# sum(all.values())
                        },
                "nodes": nodes
                }
        return stats
    
    def get_network_info(self):
        me = node.fulladdr+":"+str(node.port)
        node.network[me] = [f"{ip}:{porta}" for ip, porta in node.peers]
        network_info = node.network
        return network_info


def run_http(port):
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SudokuHTTPRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configurações de rede", add_help=False)
    parser.add_argument("-p", "--port-http", type=int, help="Porto HTTP do nó")
    parser.add_argument("-s", "--port-p2p", type=int, help="Porto do protocolo P2P do nó")
    parser.add_argument("-a", "--peer-address", type=str, help="Endereço e porto do nó da rede P2P a que se pretende juntar", required=False)
    parser.add_argument("-h", "--handicap", type=int, help="Handicap/atraso para a função de validação em milisegundos")

    args = parser.parse_args()

    print("Argumentos fornecidos:")
    print("- Porto HTTP:", args.port_http)
    print("- Porto P2P:", args.port_p2p)
    print("- Endereço P2P para conectar-se:", args.peer_address)
    print("- Handicap:", args.handicap)

    node = Peer(args)
    node.start()

    run_http(args.port_http)