import argparse
from src.node import run_http
from src.Peer import Peer

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

    run_http(args.port_http, node)