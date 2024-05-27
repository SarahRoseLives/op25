#!/usr/bin/python

import socket
import threading
import subprocess
import csv

# Requires screen to be installed on host
# Install and run script from op25 apps folder
session_name = 'OP25_SESSION'

def kill_session():
    subprocess.Popen(f"screen -S {session_name} -X quit", shell=True)


def read_trunk_file(file_path):
    # Read the TSV file into a list of dictionaries
    with open(file_path, mode='r', newline='') as file:
        reader = csv.DictReader(file, delimiter='\t', quoting=csv.QUOTE_ALL)
        data = [row for row in reader]
    return data


def modify_trunk_file(data, updates):
    # Update the first (and only) row with the provided dictionary of updates
    for key, value in updates.items():
        if key in data[0]:
            data[0][key] = value
    return data


def save_trunk_file(data, file_path):
    # Save the modified data back to the TSV file
    with open(file_path, mode='w', newline='') as file:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='\t', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)


def parse_write_config(data_str):
    updates = {}
    key_value_pairs = data_str.split(', ')
    for pair in key_value_pairs:
        if ': ' in pair:
            key, value = pair.split(': ', 1)
            updates[key] = value
    return updates


def handle_client(client_socket):
    with client_socket:
        print(f"Connection from {client_socket.getpeername()} has been established.")
        while True:
            try:
                command = client_socket.recv(1024).decode()
                if not command:
                    break

                print(f"Received command: {command}")

                if command == 'HELLO':
                    response = "ACK: HELLO"
                elif command == 'START_TEST':
                    op25_cmd = f"./rx.py --args 'rtl' -N 'LNA:47' -S 2500000 -x 2 -T trunk.tsv -U -X -l http:0.0.0.0:8080"
                    # Kill any existing session
                    kill_session()
                    # Run it in a screen session
                    subprocess.Popen(f"screen -dmS {session_name} {op25_cmd}", shell=True)
                    response = "ACK: OP25 started"
                elif command == 'STOP_OP25':
                    # Kill the screen session
                    kill_session()
                    response = "ACK: OP25 stopped"
                elif command == 'GET_OUTPUT':
                    # Capture and return the output of the screen session
                    output = subprocess.check_output(
                        f"screen -S {session_name} -X hardcopy -h /tmp/screenlog.0 && cat /tmp/screenlog.0", shell=True)
                    response = output.decode('utf-8')
                elif command == 'GET_CONFIG':
                    try:
                        file_path = 'trunk.tsv'
                        data = read_trunk_file(file_path)
                        if data:
                            config = data[0]
                            control_channel_list = config.get('Control Channel List', '')
                            sysname = config.get('Sysname', '')
                            talkgroup_list_name = config.get('Talkgroup Tags File', '')
                            response = f"Control Channel List: {control_channel_list}, Sysname: {sysname}, Talkgroup List Name: {talkgroup_list_name}"
                        else:
                            response = "NACK: No data found in trunk.tsv"
                    except Exception as e:
                        response = f"NACK: Error reading config - {str(e)}"
                elif command.startswith('WRITE_CONFIG'):
                    try:
                        # Extract the data part after the command
                        data_str = command.split(';', 1)[1]
                        # Parse the data part into key-value pairs
                        updates = parse_write_config(data_str)

                        file_path = 'trunk.tsv'
                        # Read the current data
                        data = read_trunk_file(file_path)
                        if data:
                            # Modify the data
                            data = modify_trunk_file(data, updates)
                            # Save the modified data
                            save_trunk_file(data, file_path)
                            response = "ACK: Config updated"
                        else:
                            response = "NACK: No data found in trunk.tsv"
                    except Exception as e:
                        response = f"NACK: Error updating config - {str(e)}"
                else:
                    response = "NACK: Unknown command"

                client_socket.send(response.encode())
            except ConnectionResetError:
                print("Client disconnected abruptly.")
                break

        print(f"Connection from {client_socket.getpeername()} has been closed.")


def start_server(host='0.0.0.0', port=8081):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()


if __name__ == "__main__":
    start_server()
