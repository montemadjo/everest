import socket
from uhf_reader.constants import GET_FIRMWARE_VERSION, CLEAR_READER_BUFFER, SCAN_FOR_TAGS, GET_TAG_DATA

class UHFReader:
    """
    UHF reader MR6211E
    """
    buffer_size = 1024
    connection = None
    timeout = 5.0
    port = 100
    host = None

    def __init__(self, host, port):
        self.port = port
        self.host = host

    def connect(self) -> None:
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.host, self.port))
        except Exception as ex:
            raise NetworkException("Failed to connect: " + str(ex))

    def disconnect(self) -> None:
        """
        Close connection to the reader
        """
        try:
            self.connection.close()
        except Exception as ex:
            raise NetworkException("Failed to disconnect: " + str(ex))
        
    def get_firmware_version(self) -> bytes:
        try:
            message = bytes.fromhex(GET_FIRMWARE_VERSION)
            self.connection.send(message)
            data = self.connection.recv(self.buffer_size)
            return data
        except Exception as ex:
            raise Exception("Cannot proccess command get_firmware_version" + str(ex))

    def clear_reader_buffer(self) -> bytes:
        try:
            message = bytes.fromhex(CLEAR_READER_BUFFER)
            self.connection.send(message)
            data = self.connection.recv(self.buffer_size)
            return data
        except Exception as ex:
            raise Exception("Cannot proccess command clear_reader_buffer" + str(ex))

    def scan_for_tags(self) -> bytes:
        try:
            message = bytes.fromhex(SCAN_FOR_TAGS)
            self.connection.send(message)
            data = self.connection.recv(self.buffer_size)
            return data
        except Exception as ex:
            raise Exception("Cannot proccess command scan_for_tags" + str(ex))