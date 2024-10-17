import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.is_synchronized = False  # Synchronization flag

        # Create the genesis block
        self.new_block(previous_hash='1', proof=100, message_type='enrolment', message_content={})

    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """

        print("Checking the chain is valid")

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], block['previous_hash']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            self.is_synchronized = True  # Chain is now synchronized
            return True

        return False

    def new_block(self, proof, previous_hash, message_type="standard", message_content={}):
        """
        Create a new Block in the Blockchain

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :param message_type: Type of message ('challenge', 'response' or 'enrolment')
        :param message_content: Content of the message, defaults to an empty dictionary for the genesis block
        :return: New Block
        """

        # Check if there have been any transactions
        if self.current_transactions:
            # Check if any transaction is from the sender
            for transaction in self.current_transactions:
                if transaction['sender'] != "0":  # Assuming "0" is the mining reward sender
                    message_type = "response"
                    break

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'message_type': message_type,
            'message_content': message_content
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)

        # Process the block if the chain is synchronized
        if self.is_synchronized:
            self.process_block(block)

        return block

    def new_transaction(self, sender, recipient, amount, function_name=None, function_parameter=None):
        if function_parameter is not None:
            try:
                function_parameter = int(function_parameter)
            except ValueError:
                raise ValueError('function_parameter must be an integer')
        """ 
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :param function_name: Name of the function to execute (optional)
        :param function_parameter: Parameter for the function (optional)
        :return: The index of the Block that will hold this transaction
        """
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        }

        function_map = {
            "fibonacci": self.calculate_fibonacci,
            "hash_test": self.hash_n_times,
            "factorial": self.calculate_factorial,
            "sum_natural": self.sum_natural,
        }

        if function_name in function_map:
            transaction['function_name'] = function_name
            transaction['function_result'] = function_map[function_name](function_parameter)

        self.current_transactions.append(transaction)

        return self.last_block['index'] + 1

    @staticmethod
    def calculate_fibonacci(n):
        """
        Calculate the n. term of the Fibonacci sequence

        :param n: The term of the Fibonacci sequence to calculate
        :return: The nth term
        """
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

    @staticmethod
    def hash_n_times(n):
        """
        Hash a predefined internal hash n times

        :param n: Number of times to hash the base hash
        :return: Resulting hash after N times
        """
        base_hash = "internalhashvalue"
        current_hash = hashlib.sha256(base_hash.encode()).hexdigest()
        for _ in range(n - 1):
            current_hash = hashlib.sha256(current_hash.encode()).hexdigest()
        return current_hash

    @staticmethod
    def calculate_factorial(n):
        """
        Calculate the factorial of a given number.

        :param n: The term to calculate the factorial for
        :return: The factorial of n
        """
        if n < 0:
            return "Undefined for negative values"
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    @staticmethod
    def sum_natural(n):
        """
        Calculate the sum of all natural numbers up to n.

        :param n: The number up to which the sum is calculated
        :return: The sum of all natural numbers up to n
        """
        if n < 0:
            return "Undefined for negative values"
        return n * (n + 1) // 2

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof

        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        print(proof)
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.

        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @staticmethod
    def hash_message(transaction):
        """
        Create a hashed message as a response.

        :param transaction: The transaction to be hashed.
        :return: A hashed string representing the response.
        """
        message = f"Response to transaction {transaction['sender']} -> {transaction['recipient']}: {transaction['amount']}"
        return hashlib.sha256(message.encode()).hexdigest()


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash, message_type="standard")

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'message_type': block['message_type'],
        'message_content': block['message_content']
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(
        sender=values['sender'],
        recipient=values['recipient'],
        amount=values['amount'],
        function_name=values.get('function_name'),
        function_parameter=values.get('function_parameter')
    )

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/id', methods=['GET'])
def get_node_id():
    # Retrieve the unique identifier of the node
    response = {'node_id': node_identifier}
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port, debug=True)