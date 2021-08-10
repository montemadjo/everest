from uhf_reader import UHFReader
import time

if __name__ == '__main__':
    reader = UHFReader('192.168.1.200', 100)
    reader.connect()

    data = reader.get_firmware_version()

    print("podaci: " + str(data))

    # start scanning for tags
    for i in range(0, 50):
        clr = reader.clear_reader_buffer()
        tgs = reader.scan_for_tags()
        print("print " + str(tgs))
        time.sleep(0.1)

    reader.disconnect()

    print("goodbye!")