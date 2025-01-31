#!/usr/bin/python

import socket
import threading
import subprocess
import csv
import re

from radioreference import GetSystems

# Requires screen to be installed on host
# Install and run script from op25 apps folder
session_name = 'OP25_SESSION'


def read_trunk():
    trunkfile = 'trunk.tsv'
    print(f"Opening file: {trunkfile}")  # Debug statement

    data = []  # List to store all rows as dictionaries

    with open(trunkfile, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            sysname = row.get('Sysname', 'N/A')
            control_channel_list = row.get('Control Channel List', 'N/A')
            offset = row.get('Offset', 'N/A')
            nac = row.get('NAC', 'N/A')
            modulation = row.get('Modulation', 'N/A')
            tgid_tags_file = row.get('TGID Tags File', 'N/A')
            whitelist = row.get('Whitelist', 'N/A')
            blacklist = row.get('Blacklist', 'N/A')
            center_frequency = row.get('Center Frequency', 'N/A')

            # Create a dictionary for the current row
            row_data = {
                'sysname': sysname,
                'cclist': control_channel_list,
                'offset': offset,
                'nac': nac,
                'modulation': modulation,
                'tglist': tgid_tags_file,
                'whitelist': whitelist,
                'blacklist': blacklist,
                'centerfrequency': center_frequency
            }

            # Add the dictionary to the list
            data.append(row_data)

    return data




def write_trunk(**kwargs):
    trunkfile = 'trunk.tsv'
    print(f"Writing to file: {trunkfile}")  # Debug statement

    # Define the field names
    fieldnames = ['Sysname', 'Control Channel List', 'Offset', 'NAC', 'Modulation', 'TGID Tags File', 'Whitelist',
                  'Blacklist', 'Center Frequency']

    # Prepare the row with default values
    row_data = {
        'Sysname': f'"{kwargs.get("sysname", "N/A")}"',
        'Control Channel List': f'"{kwargs.get("cclist", "N/A")}"',
        'Offset': f'"{kwargs.get("offset", "0")}"',
        'NAC': f'"{kwargs.get("nac", "0")}"',
        'Modulation': f'"{kwargs.get("modulation", "cqpsk")}"',
        'TGID Tags File': f'"{kwargs.get("tglist", "")}"',
        'Whitelist': '""',
        'Blacklist': '""',
        'Center Frequency': '""'
    }

    # Open the file for writing
    with open(trunkfile, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', quoting=csv.QUOTE_NONNUMERIC)

        # Write the header
        writer.writeheader()

        # Write the row
        writer.writerow({key: value.strip('"') for key, value in row_data.items()})


def kill_session():
    subprocess.Popen(f"screen -S {session_name} -X quit", shell=True)


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
                elif command.startswith('MANUAL_START'):
                    parts = command.split(';')

                    # Extracted values
                    sdr = parts[1]
                    gain = parts[2]

                    op25_cmd = f"./rx.py --args '{sdr}' -N 'LNA:{gain}' -S 1400000 -x 2 -T trunk.tsv -U -X -l http:0.0.0.0:8080"

                    # Kill any existing session
                    kill_session()

                    # Run it in a screen session
                    subprocess.Popen(f"screen -dmS {session_name} {op25_cmd}", shell=True)
                    print(f"Started OP25 With: {op25_cmd}")
                    response = "ACK: OP25 started"

                elif command.startswith('START_SYSTEM'):
                    try:
                        parts = command.split(';')

                        # Extracted values
                        site_id = parts[1]
                        system_id = parts[2]

                        op25_cmd = f"./rx.py --args 'rtl-sdr' -N 'LNA:48' -S 1400000 -x 2 -T systems/{system_id}/{system_id}_{site_id}_trunk.tsv -U -X -l http:0.0.0.0:8080"

                        # Kill any existing session
                        kill_session()

                        # Run it in a screen session
                        subprocess.Popen(f"screen -dmS {session_name} {op25_cmd}", shell=True)
                        print(f"Started OP25 With: {op25_cmd}")
                        response = "ACK: OP25 started"
                    except:
                        response = "ACK"


                elif command.startswith('SITELOCK'):
                    try:
                        parts = command.split(';')

                        # Extracted values
                        system_id = parts[1]
                        site_id = parts[2]

                        op25_cmd = f"./rx.py --args 'rtl-sdr' -N 'LNA:48' -S 1400000 -x 2 -T systems/{system_id}/{system_id}_{site_id}_trunk.tsv -U -X -v 9 -l http:0.0.0.0:8080"

                        # Kill any existing session
                        kill_session()

                        # Run it in a screen session
                        subprocess.Popen(f"screen -dmS {session_name} {op25_cmd}", shell=True)
                        print(f"Started OP25 With: {op25_cmd}")
                        response = "ACK: OP25 started"
                    except:
                        response = "ACK"



                elif command == 'STOP_OP25':
                    # Kill the screen session
                    kill_session()
                    response = "ACK: OP25 stopped"
                elif command == 'GET_OUTPUT':
                    # Capture and return the output of the screen session
                    output = subprocess.check_output(
                        f"screen -S {session_name} -X hardcopy -h /tmp/screenlog.0 && cat /tmp/screenlog.0", shell=True)
                    response = output.decode('utf-8')

                elif command == 'INCREASE_VOLUME':
                    subprocess.Popen("amixer set PCM 200+", shell=True)
                elif command == 'DECREASE_VOLUME':
                    subprocess.Popen("amixer set PCM 200-", shell=True)

                elif command.startswith('CREATE_SYSTEM'):
                    parts = command.split(';')

                    username = parts[1]
                    password = parts[2]
                    system_id = parts[3]

                    client = GetSystems(username=username, password=password)
                    client.create_system_tsv_files(system_id)


                    response = "ACK" # System created

                elif command == 'READ_TRUNK':
                    try:
                        trunk_data = read_trunk()
                        sysname = [entry['sysname'] for entry in trunk_data][0]
                        cclist = [entry['cclist'] for entry in trunk_data][0]
                        tglist = [entry['tglist'] for entry in trunk_data][0]



                        response = f"sysname={sysname};cclist={cclist};tglist={tglist}"
                        print(response)  # Print for debug purposes

                    except Exception as e:
                        response = f"NACK: Error reading config - {str(e)}"
                        print(response)  # Print for debug purposes

                elif command.startswith('WRITE_SCANMODE'):

                    try:
                        # Extract the system ID and mode from the command
                        parts = command.split(';')
                        system_id = parts[1].split('=')[1].strip()  # Extract system ID
                        scan_mode = parts[2].split('=')[1].strip()  # Extract scan mode

                        # Define the file path
                        file_path = f"systems/{system_id}/{system_id}_blacklist.tsv"

                        # Handle the scan mode
                        if 'system' in scan_mode:
                            print('system scan')
                            # Empty the file
                            with open(file_path, 'w') as file:
                                file.write('')

                            response = f"ACK: System scan mode for system {system_id}"

                        elif 'grid' in scan_mode:
                            print('grid scan')

                            # Write "0\t999999" to the file
                            with open(file_path, 'w') as file:
                                file.write('0\t99999')

                            response = f"ACK: Grid scan mode for system {system_id}"

                        else:

                            # Handle unexpected scan mode

                            response = f"NACK: Unknown scan mode '{scan_mode}' for system {system_id}"


                    except Exception as e:

                        # Handle any exceptions and set a response

                        response = f"NACK: Error updating scan mode - {str(e)}"



                elif command.startswith('WRITE_WHITELIST'):
                    try:
                        # Split the command into parts
                        parts = command.split(';')

                        # Extract the system ID
                        system_id = parts[1]

                        # Define the file path
                        file_path = f"systems/{system_id}/{system_id}_whitelist.tsv"

                        # Extract the whitelist entries
                        whitelist_entries = parts[2:]

                        # Format the entries as tab-separated values
                        formatted_entries = [entry.replace(':', '\t') for entry in whitelist_entries]

                        # Write the formatted entries to the whitelist file
                        with open(file_path, 'w') as file:
                            for entry in formatted_entries:
                                file.write(entry + '\n')

                        # Set a success response
                        response = "ACK - Whitelist updated successfully"

                    except Exception as e:
                        # Handle any exceptions and set a response
                        response = f"NACK - {str(e)}"




                elif command.startswith('WRITE_TRUNK'):
                    try:
                        match = re.match(r'WRITE_TRUNK;sysname=(.*?);cclist=(.*?);tglist=(.*)', command)
                        if match:
                            sysname = match.group(1)
                            cclist = match.group(2)
                            tglist = match.group(3)
                            print("sysname:", sysname)
                            print("cclist:", cclist)
                            print("tglist:", tglist)

                            write_trunk(sysname=sysname, cclist=cclist, tglist=tglist)
                            response = 'ACK'
                    except Exception as e:
                        response = f"NACK: Error updating trunk config - {str(e)}"

                # Send the response back to the client
                client_socket.send(response.encode('utf-8'))

            except ConnectionResetError:
                print("Client disconnected abruptly.")
                break

        print(f"Connection from {client_socket.getpeername()} has been closed.")


def start_server(host='0.0.0.0', port=8081):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Set the SO_REUSEADDR option
    server.bind((host, port))
    server.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()


if __name__ == "__main__":
    start_server()
