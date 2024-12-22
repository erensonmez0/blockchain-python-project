import subprocess
import requests
import os
import psutil
import time


def launch_nodes(node_count, base_port=5000):
    processes = []  # To keep track of launched processes.
    project_dir = "/home/eren/folderr1/FlaskBlockChain"  # Change this to the correct path of your project.
    venv_activate = "source /home/eren/folderr1/venv/bin/activate"  # Path to your virtual environment activation script.

    for i in range(node_count):
        port = base_port + i  # Assign a unique port to each node.

        # Command to activate venv, change directory, and run the Python app
        command = f"""
        bash -c "
        {venv_activate} &&
        cd {project_dir} &&
        python3 FlaskBlockChain.py --port {port}
        "
        """
        # Run the command in a subprocess.
        process = subprocess.Popen(
            command,
            shell=True,  # Required to run the compound bash command.
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


def get_node_hashes(ports):
    """Fetches the unique hash identifiers for all nodes."""
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
    """Create a transaction dynamically with hash-based node identifiers."""
    print("\n--- Create a Transaction ---")
    print(f"Available nodes: {', '.join(map(str, ports))}")
    sender_port = int(input("Enter sender node port: ").strip())
    recipient_port = int(input("Enter recipient node port: ").strip())
    function_name = input("Enter function name (e.g., fibonacci, sum_natural): ").strip()
    function_parameter = input("Enter function parameter (integer): ").strip()
    parent_hash = None  # Initialize parent hash to None

    # Map ports to their corresponding hashes
    sender_hash = node_hashes.get(sender_port)
    recipient_hash = node_hashes.get(recipient_port)

    if not sender_hash or not recipient_hash:
        print("Error: Invalid sender or recipient port.")
        return

    # Prepare transaction data
    transaction_data = {
        "sender": sender_hash,
        "recipient": recipient_hash,
        "transaction_type": "request",
    }

    if function_name:
        transaction_data["function_name"] = function_name
    if function_parameter:
        transaction_data["function_parameter"] = int(function_parameter)
    if parent_hash:  # Add parent hash only for response transactions
        transaction_data["parent"] = parent_hash

    # Send the transaction to the recipient node
    node_url = f"http://localhost:{recipient_port}/transactions/new"
    try:
        response = requests.post(node_url, json=transaction_data)
        if response.status_code == 201:
            print("Transaction successfully created:", response.json())
        else:
            print("Failed to create transaction:", response.text)
    except requests.RequestException as e:
        print(f"Error sending transaction to node {recipient_port}: {e}")


def terminate_nodes(processes):
    """
    Properly terminate all launched nodes and clean up any leftover processes.
    """
    print("\nTerminating all nodes...")
    for port, process in processes:
        try:
            # Terminate the process
            process.terminate()
            process.wait(timeout=5)  # Wait for the process to terminate gracefully
            print(f"Node at http://localhost:{port} terminated.")
        except subprocess.TimeoutExpired:
            print(f"Node at http://localhost:{port} did not terminate in time. Killing it.")
            process.kill()  # Force kill the process
            process.wait()  # Ensure the process is finished
        except Exception as e:
            print(f"Error while terminating node at http://localhost:{port}: {e}")

    # Ensure no leftover processes are running on the ports
    clean_ports([p[0] for p in processes])


def clean_ports(ports):
    """
    Kill any processes that are still using the specified ports.
    """
    for port in ports:
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info["cmdline"]
                if cmdline and any(str(port) in arg for arg in cmdline):
                    proc.kill()  # Forcefully kill the process using the port
                    print(f"Killed leftover process on port {port}.")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue


def interactive_menu(processes, ports, node_hashes):
    """Displays an interactive menu for user operations."""
    while True:
        print("\n--- Node Management Menu ---")
        print("1. Create a transaction")
        print("2. Terminate all nodes")
        print("--------------------------------")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            create_transaction(ports, node_hashes)
        elif choice == "2":
            print("Terminating all nodes...")
            terminate_nodes(processes)
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    node_count = int(input("How many nodes do you want to launch? "))
    base_port = 5000  # Starting port number.

    # Step 1: Launch the nodes
    launched_nodes = launch_nodes(node_count)

    print("Registering nodes with each other...")
    time.sleep(3)

    # Step 2: Register the nodes with each other.
    ports = [base_port + i for i in range(node_count)]
    register_nodes(ports)

    # Step 3: Fetch node hashes
    print("Fetching node identifiers...")
    node_hashes = get_node_hashes(ports)  # Fetch node hashes

    # Step 4: Display interactive menu
    interactive_menu(launched_nodes, ports, node_hashes)