import subprocess
import requests
import os
import psutil
import random
import time


# -------------------- Node Management Functions -------------------- #
def launch_nodes(node_count, base_port=5000):
    processes = []
    project_dir = "/home/eren/folderr1/FlaskBlockChain"
    venv_activate = "source /home/eren/folderr1/venv/bin/activate"

    for i in range(node_count):
        port = base_port + i
        command = f"""
        bash -c "
        {venv_activate} &&
        cd {project_dir} &&
        python3 FlaskBlockChain.py --port {port}
        "
        """
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append((port, process))
        print(f"Node launched at http://localhost:{port}")

    return processes


def register_nodes(ports):
    base_url = "http://localhost"
    for port in ports:
        node_url = f"{base_url}:{port}"
        for other_port in ports:
            try:
                response = requests.post(
                    f"{node_url}/nodes/register",
                    json={"nodes": [f"{base_url}:{other_port}"]}
                )
                if response.status_code == 201:
                    print(f"Node {port} registered {other_port} successfully.")
            except requests.RequestException as e:
                print(f"Failed to register node {other_port} to {port}: {e}")


def terminate_nodes(processes):
    print("\nTerminating all nodes...")
    for port, process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
            print(f"Node at http://localhost:{port} terminated.")
        except subprocess.TimeoutExpired:
            print(f"Node at http://localhost:{port} did not terminate in time. Killing it.")
            process.kill()
            process.wait()
        except Exception as e:
            print(f"Error while terminating node at http://localhost:{port}: {e}")

    clean_ports([p[0] for p in processes])


def clean_ports(ports):
    for port in ports:
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info["cmdline"]
                if cmdline and any(str(port) in arg for arg in cmdline):
                    proc.kill()
                    print(f"Killed leftover process on port {port}.")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue


# -------------------- Blockchain Interaction Functions -------------------- #

def assign_coordinator(ports):
    """
    Randomly assign a coordinator from the available nodes.
    """
    if not ports:
        print("No nodes available to assign as coordinator.")
        return None
    coordinator = random.choice(ports)
    print(f"Coordinator assigned: Node {coordinator}")
    return coordinator


def manual_verify_latest_block(ports):
    """
    Manually verify all transactions in the latest block.
    """

    coordinator_port = assign_coordinator(ports)
    chain = fetch_chain(coordinator_port)
    if not chain:
        print("Could not fetch blockchain.")
        return

    latest_block = chain[-2]
    print(f"Latest Block Index: {latest_block['index']}")
    for transaction in latest_block['transactions']:
        transaction_hash = transaction['hash']
        print(f"Verifying transaction {transaction_hash}...")

        # Call the trigger_verification endpoint
        try:
            response = requests.post(
                f"http://localhost:{coordinator_port}/trigger_verification",
                json={"transaction_hash": transaction_hash}
            )
            if response.status_code == 200:
                print(response.json()['message'])
            else:
                print(f"Verification failed: {response.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            print(f"Error during verification: {e}")


def fetch_chain(port):
    try:
        response = requests.get(f"http://localhost:{port}/chain")
        if response.status_code == 200:
            return response.json()['chain']
        else:
            print(f"Failed to fetch chain from port {port}. Response: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching chain from port {port}: {e}")
        return None


def verify_request(port, request_hash):
    try:
        response = requests.post(
            f"http://localhost:{port}/verify_request",
            json={"request_hash": request_hash}
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to verify request. Response: {response.status_code}, {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error verifying request at port {port}: {e}")
        return None


def get_node_hashes(ports):
    node_hashes = {}
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/id")
            if response.status_code == 200:
                node_hash = response.json().get("node_id")
                node_hashes[port] = node_hash
                print(f"Node {port} -> Hash: {node_hash}")
            else:
                print(f"Failed to fetch ID for node {port}")
        except requests.RequestException as e:
            print(f"Error fetching ID for node {port}: {e}")
    return node_hashes


def create_transaction(ports, node_hashes):
    print("\n--- Create a Transaction ---")
    print(f"Available nodes: {', '.join(map(str, ports))}")
    sender_port = int(input("Enter sender node port: ").strip())
    recipient_port = int(input("Enter recipient node port: ").strip())
    function_name = input("Enter function name (e.g., fibonacci, sum_natural): ").strip()
    function_parameter = input("Enter function parameter (integer): ").strip()

    sender_hash = node_hashes.get(sender_port)
    recipient_hash = node_hashes.get(recipient_port)

    if not sender_hash or not recipient_hash:
        print("Error: Invalid sender or recipient port.")
        return

    transaction_data = {
        "sender": sender_hash,
        "recipient": recipient_hash,
        "transaction_type": "request",
        "function_name": function_name,
        "function_parameter": int(function_parameter),
    }

    node_url = f"http://localhost:{recipient_port}/transactions/new"
    try:
        response = requests.post(node_url, json=transaction_data)
        if response.status_code == 201:
            print("Transaction successfully created:", response.json())
        else:
            print("Failed to create transaction:", response.text)
    except requests.RequestException as e:
        print(f"Error sending transaction to node {recipient_port}: {e}")


# -------------------- Interactive Menu -------------------- #
def interactive_menu():
    node_count = int(input("How many nodes do you want to launch? "))
    base_port = 5000
    launched_nodes = launch_nodes(node_count)

    print("Registering nodes with each other...")
    time.sleep(3)

    ports = [base_port + i for i in range(node_count)]
    register_nodes(ports)

    print("Fetching node identifiers...")
    node_hashes = get_node_hashes(ports)

    while True:
        print("\n--- Blockchain Manager Menu ---")
        print("1. Create a transaction")
        print("2. Trigger verification")
        print("3. Terminate all nodes")
        print("--------------------------------")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            create_transaction(ports, node_hashes)
        elif choice == "2":
            manual_verify_latest_block(ports)  # Use the first node as coordinator for simplicity
        elif choice == "3":
            terminate_nodes(launched_nodes)
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    interactive_menu()