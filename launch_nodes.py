import subprocess
# import requests
import os


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


"""

def register_nodes(ports):
    base_url = "http://localhost"
    for port in ports:
        node_url = f"{base_url}:{port}"
        for other_port in ports:
            if port != other_port:  # Don't register a node to itself.
                try:
                    response = requests.post(
                        f"{node_url}/nodes/register",
                        json={"nodes": [f"{base_url}:{other_port}"]}
                    )
                    if response.status_code == 201:
                        print(f"Node {port} registered {other_port} successfully.")
                except requests.RequestException as e:
                    print(f"Failed to register node {other_port} to {port}: {e}")
"""

if __name__ == "__main__":
    node_count = int(input("How many nodes do you want to launch? "))
    base_port = 5000  # Starting port number.

    # Step 1: Launch the nodes
    launched_nodes = launch_nodes(node_count)
    """
    # Step 2: Register the nodes with each other.
    ports = [base_port + i for i in range(node_count)]
    print("Registering nodes with each other...")
    register_nodes(ports)
    """

    input("Press Enter to terminate all nodes...")
    for port, process in launched_nodes:
        process.terminate()
        print(f"Node at http://localhost:{port} terminated.")
