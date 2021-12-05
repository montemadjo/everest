from uhf_reader import UHFReader
from uhf_reader import Camera
from datetime import datetime

from queue import Queue
from threading import Thread
import zmq
import logging
import time
import binascii
import json

REQUEST_TIMEOUT = 2500
REQUEST_RETRIES = 10
SERVER_ENDPOINT = "tcp://localhost:5555"
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

# a thread that produces data


def producer(out_q, r_q, q_opener, q_sender, reader):
    """
    Producer
    """
    employees = []
    vehicle = None
    route = None
    cardtype = None
    deps = []
    while True:
        # produce some data
        clr = reader.clear_reader_buffer()
        tgs = reader.scan_for_tags()

        try:
            data = r_q.get(False,1)
            command = data["command"]
            if command == "VEHICLE NEED ALL":
                reader.activate_output_0_flag = True
                # vehicle
                cardtype = "vehicle"
                deps = ["route", "employee"]
                vehicle = data["card"]
            elif command == "EMPLOYEE NEED ALL":
                reader.activate_output_1_flag = True
                # employee
                cardtype = "employee"
                deps = ["route", "vehicle"]
                employees.append(data["card"])
            elif command == "ROUTE NEED ALL":
                reader.activate_output_2_flag = True
                # route
                cardtype = "route"
                deps = ["vehicle", "employee"]
                route = data["card"]
            elif command == "EMPLOYEE NEED VEHICLE":
                reader.activate_output_1_flag = True
                # employee
                cardtype = "employee"
                deps = ["vehicle"]
                if data["card"] not in employees:
                    employees.append(data["card"])
            elif command == "VEHICLE NEED EMPLOYEE":
                reader.activate_output_0_flag = True
                # vehicle
                cardtype = "vehicle"
                deps = ["employee"]
                vehicle = data["card"]
            elif command == "FAST EMPLOYEE":
                # superemployee
                cardtype = "employee"
                if data["card"] not in employees:
                    employees.append(data["card"])
                # route = data["card"]
                # reader.activate_output_0_flag = True
                reader.activate_output_1_flag = True
                # reader.activate_output_2_flag = True
            elif command == "FAST VEHICLE":
                # supervehicle
                cardtype = "vehicle"
                vehicle = data["card"]
                # route = data["card"]
                reader.activate_output_0_flag = True
                # reader.activate_output_1_flag = True
                # reader.activate_output_2_flag = True

        except: # queue here refers to the module, not a class
            pass

        # if card is succesfully read wait for other cards
        if reader.activate_output_0_flag is True or reader.activate_output_1_flag is True or reader.activate_output_2_flag:
            reader.count -= 1
            # print(reader.count)

            if command == "VEHICLE NEED ALL" or command == "EMPLOYEE NEED ALL" or command == "ROUTE NEED ALL":
                # if all flags are up open the gate:
                if reader.activate_output_0_flag is True and reader.activate_output_1_flag is True and reader.activate_output_2_flag is True:
                    if reader.count_locker is True:
                        reader.count = 20
                        reader.count_locker = False
                        print ("OPEN THE DOOR!")
                        q_opener.put("OPEN THE DOOR!")
            
            elif command == "EMPLOYEE NEED VEHICLE" or command == "VEHICLE NEED EMPLOYEE":
                # if vehicle and employee flags are up open the gate:
                if reader.activate_output_0_flag is True and reader.activate_output_1_flag is True:
                    if reader.count_locker is True:
                        reader.count = 20
                        reader.count_locker = False
                        print ("OPEN THE DOOR!")
                        q_opener.put("OPEN THE DOOR!")

            elif command == "FAST EMPLOYEE" or command == "FAST VEHICLE":
                # open the gate bezuslovno
                if reader.count_locker is True:
                    reader.count = 20
                    reader.count_locker = False
                    print ("OPEN THE DOOR!")
                    q_opener.put("OPEN THE DOOR!")                
        
        if reader.count < 200 and reader.count >= 20:
            if cardtype == "vehicle":
                reader.set_output0(True)
            if cardtype == "employee":
                reader.set_output1(True)
            if cardtype == "route":
                reader.set_output2(True)
            if "vehicle" in deps:
                reader.blink_output0()
            if "employee" in deps:
                reader.blink_output1()
            if "route" in deps:
                reader.blink_output2()

            # if reader.activate_output_0_flag:
            #     reader.blink_output0()
            # if reader.activate_output_1_flag:
            #     reader.blink_output1()
            # if reader.activate_output_2_flag:
            #     reader.blink_output2()

        # counter is about to expire
        # if reader.count < 20 and reader.count_locker is False:
        #     reader.set_output0(True)
        #     reader.set_output1(True)
        #     reader.set_output2(True)

        # counter expired.
        if reader.count == 0:
            reader.count = 200
            reader.count_locker = True
            reader.set_output0(False)
            reader.set_output1(False)
            reader.set_output2(False)
            reader.activate_output_0_flag = False
            reader.activate_output_1_flag = False
            reader.activate_output_2_flag = False

            # produce data for transfer
            # Data to be sent
            message = {
                "uhf": {
                    "id": 1,
                    "password": 21,
                    "command": "card read"
                },
                "employees": employees,
                "vehicle": vehicle,
                "route": route,
                "command": None
            }

            now = datetime.now()
            print(f"{now}: timer expired")
            print(message)

            q_sender.put(message)

            employees = []
            vehicle = None
            route = None
            cardtype = None
            deps = []

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
def consumer(in_q, r_q):
    i = 0
    while True:
        data = in_q.get()
        i += 1
        print(i)
        card = binascii.hexlify((bytearray(data)))
        print(card)

        # Data to be written 
        data = {
            "uhf": {
                "id": 1,
                "password": 21,
                "command": "card read"
            },
            "card": card.decode("utf-8"),
            "command": None
        }

        message = json.dumps(data)
        client.send_string(message)
        reply = client.recv()
        if reply == b'VEHICLE card found, employee and route needed!':
            data["command"] = "VEHICLE NEED ALL"
            r_q.put(data)
        elif reply == b'EMPLOYEE card found, vehicle and route needed!':
            data["command"] = "EMPLOYEE NEED ALL"
            r_q.put(data)
        elif reply == b'ROUTE card found, vehicle and employee needed!':
            data["command"] = "ROUTE NEED ALL"
            r_q.put(data)
        elif reply == b'FAST card found, type employee':
            data["command"] = "FAST EMPLOYEE"
            r_q.put(data)
        elif reply == b'FAST card found, type vehicle':
            data["command"] = "FAST VEHICLE"
            r_q.put(data)
        elif reply == b'EMPLOYEE card found, vehicle needed!':
            data["command"] = "EMPLOYEE NEED VEHICLE"
            r_q.put(data)
        elif reply == b'VEHICLE card found, employee needed!':
            data["command"] = "VEHICLE NEED EMPLOYEE"
            r_q.put(data)

        logging.info(reply)
        # time.sleep(1)

# a thread that opens the gate
def opener(q_opener):
    while True:
        data = q_opener.get()
        print(f"SENT COMMAND: {data}")
        if data == "OPEN THE DOOR!":
            camera.switchOutput(1)

# a thread that sends the data over web api


def sender(q_sender):
    while True:
        data = q_sender.get()
        print(f"send to wep api: {data}")

if __name__ == '__main__':
    reader = UHFReader('192.168.1.154', 100)
    reader.connect()
    reader.set_output0(False)
    reader.set_output1(False)
    reader.set_output2(False)

    camera = Camera("http://192.168.1.152/ISAPI/System/IO/outputs/1/trigger", "admin", "Tfs123456")

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
        t1 = Thread(target=producer, args=(q, r_q, q_opener, q_sender, reader))
        t2 = Thread(target=consumer, args=(q, r_q ))
        t3 = Thread(target=opener, args=(q_opener, ))
        t4 = Thread(target=sender, args=(q_sender, ))

        t1.start()
        t2.start()
        t3.start()
        t4.start()

    except Exception as ex:
        reader.disconnect()
        raise Exception(("Something broke: " + str(ex)))

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
