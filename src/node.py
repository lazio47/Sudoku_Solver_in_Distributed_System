import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class SudokuHTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, node=None, **kwargs):
        self.node = node
        super().__init__(*args, **kwargs)

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
                solved_puzzle = self.node.solve_sudoku(puzzle)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(solved_puzzle).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def get_stats(self):
        me = self.node.fulladdr + ":" + str(self.node.port)
        self.node.all_peers_validations[me] = self.node.my_validations
        all = self.node.all_peers_validations
        nodes = [
            {"address": endereco, "validations": validacoes} 
            for endereco, validacoes in all.items()
            if (endereco.split(":")[0], int(endereco.split(":")[1])) in self.node.peers
            or (endereco.split(":")[0], int(endereco.split(":")[1])) == (self.node.fulladdr, self.node.port)
        ]
        stats = {
            "all": {
                "solved": self.node.solved,
                "validations": self.node.all_validations
            },
            "nodes": nodes
        }
        return stats

    def get_network_info(self):
        me = self.node.fulladdr + ":" + str(self.node.port)
        self.node.network[me] = [f"{ip}:{porta}" for ip, porta in self.node.peers]
        network_info = self.node.network
        return network_info

def run_http(port, node):
    server_address = ('0.0.0.0', port)
    handler = lambda *args, **kwargs: SudokuHTTPRequestHandler(*args, node=node, **kwargs)
    httpd = HTTPServer(server_address, handler)
    httpd.serve_forever()
