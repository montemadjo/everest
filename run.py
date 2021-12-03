from uhf_reader import UHFReader
from uhf_reader import Camera

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
def producer(out_q, r_q, q_opener, reader):
    """
    Producer
    """
    employees = []
    vehicle = None
    route = None
    while True:
        # produce some data
        clr = reader.clear_reader_buffer()
        tgs = reader.scan_for_tags()

        try:
            data = r_q.get(False,1)
            if data["command"] == "VEHICLE":
                reader.activate_output_0_flag = True
                # vehicle
            elif data["command"] == "EMPLOYEE":
                reader.activate_output_1_flag = True
                # employee
            elif data["command"] == "ROUTE":
                reader.activate_output_2_flag = True
                # route
            elif data["command"] == "TURN_ALL_LIGHTS":
                # superemployee
                reader.activate_output_0_flag = True
                reader.activate_output_1_flag = True
                reader.activate_output_2_flag = True

        except: # queue here refers to the module, not a class
            pass

        # if card is succesfully read wait for other cards
        if reader.activate_output_0_flag is True or reader.activate_output_1_flag is True or reader.activate_output_2_flag:
            reader.count -= 1
            # print(reader.count)

            # if all flags are up open the gate:
            if reader.activate_output_0_flag is True and reader.activate_output_1_flag is True and reader.activate_output_2_flag is True:
                if reader.count_locker is True:
                    reader.count = 20
                    reader.count_locker = False
                    print ("OPEN THE DOOR!")
                    q_opener.put("OPEN THE DOOR!")
        
        if reader.count < 200 and reader.count >= 20:
            if reader.activate_output_0_flag:
                reader.blink_output0()
            if reader.activate_output_1_flag:
                reader.blink_output1()
            if reader.activate_output_2_flag:
                reader.blink_output2()

        # counter is about to expire
        if reader.count < 20 and reader.count_locker is False:
            reader.set_output0(True)
            reader.set_output1(True)
            reader.set_output2(True)

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
        if reply == b'VEHICLE card found, turn up light 0!':
            data["command"] = "VEHICLE"
            r_q.put(data)
        elif reply == b'EMPLOYEE card found, turn up light 1!':
            data["command"] = "EMPLOYEE"
            r_q.put(data)
        elif reply == b'ROUTE card found, turn up light 2!':
            data["command"] = "ROUTE"
            r_q.put(data)
        elif reply == b'card found, open gate!':
            data["command"] = "TURN_ALL_LIGHTS"
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
        t1 = Thread(target=producer, args=(q, r_q, q_opener, reader))
        t2 = Thread(target=consumer, args=(q, r_q ))
        t3 = Thread(target=opener, args=(q_opener, ))

        t1.start()
        t2.start()
        t3.start()

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
