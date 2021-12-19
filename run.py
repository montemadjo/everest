from uhf_reader import UHFReader
from uhf_reader import Camera
from uhf_reader import Sender
from datetime import datetime

from queue import Queue
from threading import Thread
import zmq
import logging
import time
import binascii
import json
import configparser
import argparse

import sys
import os
from distutils.util import strtobool

parser = argparse.ArgumentParser()
parser.add_argument("config", help="path to configuration file")
args = parser.parse_args()

config_path = args.config

print("config path")
print(config_path)

# load the configuration file
config = configparser.ConfigParser()
config.read(config_path)

MY_ID = int(config['Basic']['Id'])
IS_EASY_ACCESS = bool(strtobool(config['Basic']['EasyAccess']))
OPPOSITE_SIDE_MASK_TIME = int(config['Basic']['OppositeSideMaskTime'])

REQUEST_TIMEOUT = int(config['Zmq']['Timeout'])
REQUEST_RETRIES = int(config['Zmq']['Retries'])
SERVER_ENDPOINT = config['Zmq']['Endpoint']
UHF_READER_ADDRESS = config['UhfReader']['Address']
UHF_READER_PORT = int(config['UhfReader']['Port'])
CAMERA_ADDRESS = config['Camera']['Address']
CAMERA_USERNAME = config['Camera']['Username']
CAMERA_PASSWORD = config['Camera']['Password']
CAMERA_URL = "http://" + CAMERA_ADDRESS + "/ISAPI/System/IO/outputs/1/trigger"
SENDER_URL = config['Remote']['SenderUrl']

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

# a thread that produces data


def producer(out_q, r_q, q_opener, q_sender, q_wd, reader):
    """
    Producer
    """
    employees = []
    simpleemployees = []
    vehicles = []
    simplevehicles = []
    route = None
    cardtypes = []
    deps = []
    simpleflag_vehicle = False
    simpleflag_employee = False
    simple_count_locker = True
    simplecount = 20
    given_liting_command_0 = False
    given_liting_command_1 = False
    given_liting_command_2 = False
    while True:
        # produce some data
        clr = reader.clear_reader_buffer()
        tgs = reader.scan_for_tags()

        # watchdog informer
        q_wd.put("producer_alive")

        try:
            data = r_q.get(False, 1)
            command = data["command"]
            if command == "VEHICLE NEED ALL":
                reader.activate_output_0_flag = True
                # vehicle
                cardtypes.append("vehicle")
                if "route" not in deps:
                    deps.append("route")
                if "employee" not in deps:
                    deps.append("employee")
                vehicles.append(data["card"])
            elif command == "EMPLOYEE NEED ALL":
                reader.activate_output_1_flag = True
                # employee
                cardtypes.append("employee")
                if "route" not in deps:
                    deps.append("route")
                if "vehicle" not in deps:
                    deps.append("vehicle")
                # if data["card"] not in employees:
                employees.append(data["card"])
            elif command == "ROUTE NEED ALL":
                reader.activate_output_2_flag = True
                # route
                cardtypes.append("route")
                if "employee" not in deps:
                    deps.append("employee")
                if "vehicle" not in deps:
                    deps.append("vehicle")
                deps = ["vehicle", "employee"]
                route = data["card"]
            elif command == "EMPLOYEE NEED VEHICLE":
                reader.activate_output_1_flag = True
                # employee
                cardtypes.append("employee")
                if "vehicle" not in deps:
                    deps.append("vehicle")
                # if data["card"] not in employees:
                employees.append(data["card"])
            # elif command == "SIMPLEEMPLOYEE NEED SIMPLEVEHICLE":
            #     # reader.activate_output_1_flag = True
            #     # simpleemployee
            #     print("SIMPLEEMPLOYEE NEED SIMPLEVEHICLE")
            #     cardtypes.append("simpleemployee")
            #     if "simplevehicle" not in deps:
            #         deps.append("simplevehicle")
            #     # if data["card"] not in simpleemployees:
            #     simpleemployees.append(data["card"])
            elif command == "VEHICLE NEED EMPLOYEE":
                reader.activate_output_0_flag = True
                # vehicle
                cardtypes.append("vehicle")
                if "employee" not in deps:
                    deps.append("employee")
                vehicles.append(data["card"])
            elif command == "FAST EMPLOYEE":
                # superemployee
                cardtypes.append("employee")
                if data["card"] not in employees:
                    employees.append(data["card"])
                # route = data["card"]
                # reader.activate_output_0_flag = True
                reader.activate_output_1_flag = True
                # reader.activate_output_2_flag = True
            elif command == "FAST SIMPLEVEHICLE":
                # supervehicle
                cardtypes.append("simplevehicle")
                simplevehicles.append(data["card"])
                # route = data["card"]
                simpleflag_vehicle = True
                # reader.activate_output_1_flag = True
                # reader.activate_output_2_flag = True
            elif command == "SIMPLEVEHICLE NEED SIMPLEEMPLOYEE":
                # supervehicle
                cardtypes.append("simplevehicle")
                print("SIMPLEVEHICLE NEED SIMPLEEMPLOYEE")
                simplevehicles.append(data["card"])
                simpleflag_vehicle = True
                # route = data["card"]
                # reader.activate_output_1_flag = True
                # reader.activate_output_2_flag = True
            elif command == "SIMPLEEMPLOYEE NEED SIMPLEVEHICLE":
                # supervehicle
                cardtypes.append("simpleemployee")
                simpleemployees.append(data["card"])
                print("SIMPLEEMPLOYEE NEED SIMPLEVEHICLE")
                simpleflag_employee = True
                # route = data["card"]
                # reader.activate_output_1_flag = True
                # reader.activate_output_2_flag = True

        except:  # queue here refers to the module, not a class
            pass

        # if card is succesfully read wait for other cards
        if reader.activate_output_0_flag is True or reader.activate_output_1_flag is True or reader.activate_output_2_flag:
            reader.count -= 1
            # print(reader.count)

            if command == "VEHICLE NEED ALL" or command == "EMPLOYEE NEED ALL" or command == "ROUTE NEED ALL":
                # if all flags are up open the gate:
                if reader.activate_output_0_flag is True and reader.activate_output_1_flag is True and reader.activate_output_2_flag is True:
                    if reader.count_locker is True:
                        reader.count = 30
                        reader.count_locker = False
                        print("OPEN THE DOOR!")
                        q_opener.put("OPEN THE DOOR!")

            if command == "VEHICLE NEED ALL" and IS_EASY_ACCESS is True:
                if reader.count_locker is True:
                    reader.count = 20
                    reader.count_locker = False
                    print("OPEN THE DOOR FAST!")
                    q_opener.put("OPEN THE DOOR!")

            elif command == "EMPLOYEE NEED VEHICLE" or command == "VEHICLE NEED EMPLOYEE":
                # if vehicle and employee flags are up open the gate:
                if reader.activate_output_0_flag is True and reader.activate_output_1_flag is True:
                    if reader.count_locker is True:
                        reader.count = 20
                        reader.count_locker = False
                        print("OPEN THE DOOR!")
                        q_opener.put("OPEN THE DOOR!")

            elif command == "FAST EMPLOYEE":
                # open the gate bezuslovno
                if reader.count_locker is True:
                    reader.count = 20
                    reader.count_locker = False
                    print("OPEN THE DOOR!")
                    q_opener.put("OPEN THE DOOR!")

        # if card is succesfully read wait for other cards
        if simpleflag_employee is True or simpleflag_vehicle is True:
            simplecount -= 1
            # print(reader.count)

            if command == "SIMPLEVEHICLE NEED SIMPLEEMPLOYEE" or command == "SIMPLEEMPLOYEE NEED SIMPLEVEHICLE":
                # if vehicle and employee flags are up open the gate:
                if simpleflag_employee is True and simpleflag_vehicle is True:
                    if simple_count_locker is True:
                        simplecount = 20
                        simple_count_locker = False
                        print("OPEN THE DOOR!")
                        q_opener.put("OPEN THE DOOR!")

            elif command == "FAST SIMPLEVEHICLE":
                # open the gate bezuslovno
                if simple_count_locker is True:
                    simplecount = 20
                    simple_count_locker = False
                    print("OPEN THE DOOR!")
                    q_opener.put("OPEN THE DOOR!")

        if reader.count < 200 and reader.count >= 20:
            if "vehicle" in cardtypes:
                reader.set_output0(True)
                given_liting_command_0 = True
            if "employee" in cardtypes:
                reader.set_output1(True)
                given_liting_command_1 = True
            if "route" in cardtypes:
                reader.set_output2(True)
                given_liting_command_2 = True
            if "vehicle" in deps:
                if given_liting_command_0 is False:
                    reader.blink_output0(8, 2)
            if "employee" in deps:
                if given_liting_command_1 is False:
                    reader.blink_output1(8, 2)
            if "route" in deps:
                if given_liting_command_2 is False:
                    reader.blink_output2(8, 2)

            # if reader.activate_output_0_flag:
            #     reader.blink_output0()
            # if reader.activate_output_1_flag:
            #     reader.blink_output1()
            # if reader.activate_output_2_flag:
            #     reader.blink_output2()

        # counter is about to expire
        if reader.count < 20 and reader.count_locker is False:
            if "vehicle" in cardtypes:
                reader.set_output0(True)
            if "employee" in cardtypes:
                reader.set_output1(True)
            if "route" in cardtypes:
                reader.set_output2(True)
            # if "vehicle" in cardtypes:
            #     reader.set_output0(True)
            # if "employee" in cardtypes:
            #     reader.set_output1(True)
            # if "route" in cardtypes:
            #     reader.set_output2(True)
            # if "vehicle" in deps:
            #     reader.blink_output0()
            # if "employee" in deps:
            #     reader.blink_output1()
            # if "route" in deps:
            #     reader.blink_output2()

        # counter expired.
        if reader.count == 0:
            reader.count = 200
            reader.count_locker = True
            # simplecount = 200
            # simple_count_locker = True

            reader.set_output0(False)
            reader.set_output1(False)
            reader.set_output2(False)

            reader.activate_output_0_flag = False
            reader.activate_output_1_flag = False
            reader.activate_output_2_flag = False

            given_liting_command_0 = False
            given_liting_command_1 = False
            given_liting_command_2 = False

            # produce data for transfer
            # Data to be sent
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"{now}: timer expired")

            message = {
                "uhf": {
                    "id": MY_ID,
                    "password": 21,
                    "command": "card read"
                },
                "employees": employees,
                "simpleemployees": simpleemployees,
                "vehicles": vehicles,
                "simplevehicles": simplevehicles,
                "route": route,
                "accesstime": now,
                "command": None
            }

            print(message)
            q_sender.put(message)

            employees = []
            simpleemployees = []
            vehicles = []
            route = None
            cardtypes = []
            deps = []
            # simpleflag_vehicle = False
            # simpleflag_employee = False
            simplevehicles = []

        if simplecount == 0:
            simplecount = 200
            # reader.count = 200
            # reader.count_locker = True
            simple_count_locker = True

            # reader.set_output0(False)
            # reader.set_output1(False)
            # reader.set_output2(False)

            # reader.activate_output_0_flag = False
            # reader.activate_output_1_flag = False
            # reader.activate_output_2_flag = False

            # given_liting_command_0 = False
            # given_liting_command_1 = False
            # given_liting_command_2 = False

            # produce data for transfer
            # Data to be sent
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"{now}: timer expired")

            message = {
                "uhf": {
                    "id": MY_ID,
                    "password": 222,
                    "command": "card read"
                },
                "employees": employees,
                "simpleemployees": simpleemployees,
                "vehicles": vehicles,
                "simplevehicles": simplevehicles,
                "route": route,
                "accesstime": now,
                "command": None
            }

            print(message)
            q_sender.put(message)

            # employees = []
            simpleemployees = []
            # vehicles = []
            # route = None
            cardtypes = []
            deps = []
            simpleflag_vehicle = False
            simpleflag_employee = False
            simplevehicles = []

        # wheather the result is 00 or 01
        if tgs is not b'\x00':
            #     print(binascii.hexlify(bytearray(tgs)))
            # else:
            tag = reader.get_tag_data()
            out_q.put(binascii.hexlify(bytearray(tag)))
        time.sleep(0.05)

        # ovdje treba da se stavi nešto kao
        # semafor_commander.scan_for_command()
        # i da se poziva na spoljnu komandu za upravljanje semaforom

# a thread that consumes data


def consumer(in_q, r_q, q_wd):
    i = 0
    while True:
        q_wd.put("consumer_alive")

        try:
            data = in_q.get()
            i += 1
            print(i)
            card = binascii.hexlify((bytearray(data)))
            print(card)

            # Data to be written
            data = {
                "uhf": {
                    "id": MY_ID,
                    "password": 21,
                    "command": "card read"
                },
                "card": card.decode("utf-8"),
                "command": None,
                "accesstime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            message = json.dumps(data)
            client.send_string(message)
            breply = client.recv()
            jreply = json.loads(breply)
            reply = jreply["command"]
            last_cards = jreply["last_cards"]
            print("last_cards")
            print(last_cards)

            # consider cards that are shown longer than OPPOSITE_SIDE_MASK_TIME only
            is_card_masked = False
            for item in last_cards:
                if item['card'] == card.decode("utf-8"):
                    last_access_time = datetime.strptime(
                        item["accesstime"], '%Y-%m-%d %H:%M:%S')
                    print("last access time")
                    print(last_access_time)
                    c = datetime.now() - last_access_time
                    if c.total_seconds() < OPPOSITE_SIDE_MASK_TIME:
                        is_card_masked = True
                        print("last access time total seconds:")
                        print(c)
                        print("CARD MASKED!!!")

            if is_card_masked is False:
                if reply == 'VEHICLE card found, employee and route needed!':
                    data["command"] = "VEHICLE NEED ALL"
                    r_q.put(data)
                elif reply == 'EMPLOYEE card found, vehicle and route needed!':
                    data["command"] = "EMPLOYEE NEED ALL"
                    r_q.put(data)
                elif reply == 'ROUTE card found, vehicle and employee needed!':
                    data["command"] = "ROUTE NEED ALL"
                    r_q.put(data)
                # will never happen...
                elif reply == 'FAST card found, type employee':
                    data["command"] = "FAST EMPLOYEE"
                    r_q.put(data)
                # will happen very often...
                elif reply == 'FAST card found, type simplevehicle':
                    data["command"] = "FAST SIMPLEVEHICLE"
                    r_q.put(data)
                elif reply == 'EMPLOYEE card found, vehicle needed!':
                    data["command"] = "EMPLOYEE NEED VEHICLE"
                    r_q.put(data)
                elif reply == 'SIMPLEEMPLOYEE card found, simplevehicle needed!':
                    data["command"] = "SIMPLEEMPLOYEE NEED SIMPLEVEHICLE"
                    r_q.put(data)
                elif reply == 'VEHICLE card found, employee needed!':
                    data["command"] = "VEHICLE NEED EMPLOYEE"
                    r_q.put(data)
                elif reply == 'SIMPLEVEHICLE card found, simpleemployee needed!':
                    data["command"] = "SIMPLEVEHICLE NEED SIMPLEEMPLOYEE"
                    r_q.put(data)

            now = datetime.now()

            current_time = now.strftime("%H:%M:%S")
            logging.info(current_time)
            logging.info(reply)
            # time.sleep(1)
        except:
            os._exit(1)

# a thread that opens the gate


def opener(q_opener, q_wd):
    while True:
        try:
            data = q_opener.get()
            print(f"SENT COMMAND: {data}")
            if data == "OPEN THE DOOR!":
                camera.switchOutput(1)
        except:
            os._exit(1)

# a thread that sends the data over web api


def sender(q_sender, q_wd):
    while True:
        try:
            data = q_sender.get()
            print(f"send to wep api: {data}")
            uhfsender.postStadionUhfCards(data)
        except:
            os._exit(1)


def watchdog(q_wd):
    is_sender_alive = False
    is_opener_alive = False
    is_consumer_alive = False
    is_producer_alive = False
    counter = 100

    while True:
        # watchdog will exit if every 1sec every thread don't send alive signal
        counter -= 1
        time.sleep(0.025)

        print(counter)

        if counter < 0:
            if is_sender_alive is True and is_opener_alive is True and is_consumer_alive is True and is_producer_alive is True:
                is_sender_alive = False
                is_opener_alive = False
                is_consumer_alive = False
                is_producer_alive = False
            else:
                print("Process killed by watchdog!!")
                os._exit(1)
            counter = 100
        try:
            data = q_wd.get(False)
            print('two')
            if data == "sender_alive":
                print("SENDER alive")
                is_sender_alive = True
            elif data == "opener_alive":
                print("OPENER alive")
                is_opener_alive = True
            elif data == "consumer_alive":
                print("CONSUMER alive")
                is_consumer_alive = True
            elif data == "producer_alive":
                print("PRODUCER alive")
                is_producer_alive = True
        except:
            pass


if __name__ == '__main__':
    reader = UHFReader(UHF_READER_ADDRESS, UHF_READER_PORT)
    reader.connect()
    reader.set_output0(False)
    reader.set_output1(False)
    reader.set_output2(False)

    camera = Camera(
        CAMERA_URL, CAMERA_USERNAME, CAMERA_PASSWORD)
    uhfsender = Sender(
        SENDER_URL)
    # zmq context
    context = zmq.Context()
    logging.info("connecting to server...")
    client = context.socket(zmq.REQ)
    client.connect(SERVER_ENDPOINT)

    data = reader.get_firmware_version()

    print("podaci: " + str(data))

    # reader.disconnect()

    # start scanning for tags
    try:
        q = Queue()
        r_q = Queue()
        q_opener = Queue()
        q_sender = Queue()
        q_wd = Queue()
        t1 = Thread(target=producer, args=(
            q, r_q, q_opener, q_sender, q_wd, reader))
        t2 = Thread(target=consumer, args=(q, r_q, q_wd))
        t3 = Thread(target=opener, args=(q_opener, q_wd))
        t4 = Thread(target=sender, args=(q_sender, q_wd))
        t5 = Thread(target=watchdog, args=(q_wd, ))

        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()

    except:
        print("EXCEPTION OCCURS!!!")
        sys.exit(1)

    # while True:
    #     clr = reader.clear_reader_buffer()
    #     tgs = reader.scan_for_tags()
    #     # wheather the result is 00 or 01
    #     if tgs is not b'\x00':
    #         #     print(binascii.hexlify(bytearray(tgs)))
    #         # else:
    #         tag = reader.get_tag_data()
    #         print(binascii.hexlify(bytearray(tag)))
    #     time.sleep(0.1)

    # reader.disconnect()

    print("started!")
