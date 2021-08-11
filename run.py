from uhf_reader import UHFReader
from queue import Queue
from threading import Thread
import time
import binascii

# a thread that produces data


def producer(out_q, reader):
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
        time.sleep(0.1)

# a thread that consumes data


def consumer(in_q):
    while True:
        data = in_q.get()
        print(binascii.hexlify((bytearray(data))))


if __name__ == '__main__':
    reader = UHFReader('192.168.1.200', 100)
    reader.connect()

    data = reader.get_firmware_version()

    print("podaci: " + str(data))

    # start scanning for tags
    try:
        q = Queue()
        t1 = Thread(target=producer, args=(q, reader))
        t2 = Thread(target=consumer, args=(q, ))

        t1.start()
        t2.start()

    except Exception as ex:
        reader.disconnect()
        raise Exception(("Jajara"))

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
