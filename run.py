from uhf_reader import UHFReader
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
def producer(out_q, reader):
    """
    Producer
    """
    while True:
        # produce some data
        clr = reader.clear_reader_buffer()
        tgs = reader.scan_for_tags()
        # wheather the result is 00 or 01
        if tgs is not b'\x00':
            #     print(binascii.hexlify(bytearray(tgs)))
            # else:
            tag = reader.get_tag_data()
            out_q.put(binascii.hexlify(bytearray(tag)))
        time.sleep(0.025)
        reader.set_output1(True)
        time.sleep(0.025)
        reader.set_output1(False)

        # ovdje treba da se stavi nešto kao
        # semafor_commander.scan_for_command()
        # i da se poziva na spoljnu komandu za upravljanje semaforom

# a thread that consumes data
def consumer(in_q):
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
            "card": card.decode("utf-8") 
        }

        message = json.dumps(data)
        client.send_string(message)
        reply = client.recv()
        logging.info(reply)
        # time.sleep(1)

if __name__ == '__main__':
    reader = UHFReader('192.168.1.153', 100)
    reader.connect()

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
        t1 = Thread(target=producer, args=(q, reader))
        t2 = Thread(target=consumer, args=(q, ))

        t1.start()
        t2.start()

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

    print("goodbye!")
