from typing import BinaryIO, Hashable, Iterable, Dict
from collections import deque
from os import stat

from utils import fill_deque_from_byte, bits_to_bytes


INPUT_BUFFER_SIZE = 10240


class BitSequence(Hashable): # хеширумая последовательность из битов
    """
    This class is just hashable deque if bits
    It is needed to store bit fields as the dict keys
    """

    def __init__(self, bits: Iterable[bool], use_given_deque: bool = False):
        """
        Initializes BitSequence with given iterable of bits

        :param bits: Sequence to use (copies it)
        :param use_given_deque: Is needed to speed up the initialization by using given deque instead of creating one inside
        """
        if isinstance(bits, deque) and use_given_deque:
            self.data = bits
        else:
            self.data = deque(bits)

    def __hash__(self) -> int:
        """
        Uses each bit as a part of number

        :return: Unique int representation of the bit field
        """
        result = 0
        for bit in self.data:
            result <<= 1
            result |= bit
        return result

    def __eq__(self, other) -> bool:
        """
        Compares bit sequences (or sequence with iterable) bit-by-bit

        :param other: sequence to compare with
        """
        if isinstance(other, BitSequence):
            other = other.data
        if len(self.data) != len(other):
            return False
        return all(self.data[i] == other[i] for i in range(len(self.data)))


class Decoder:
    def __init__(self, input_file: BinaryIO, output_file: BinaryIO):
        """
        Initializes the instance of decoder without reading or writing any data from/to files
        """
        self.input_file = input_file
        self.output_file = output_file
        self.coding_table: Dict[BitSequence, int] = {}
        self.decoding_buffer = deque()
        self.input_file_size = stat(self.input_file.name).st_size

    def read_header(self) -> int:
        """
        Read the header of file, parse and save it;

        :return number of trailing zeros
        """
        self.input_file.seek(0)
        trailing_zeros = int.from_bytes(self.input_file.read(1), byteorder='little') # количество нулей в конце
        table_size = int.from_bytes(self.input_file.read(4), byteorder='little') # размер таблицы в битах
        table_bytes = (table_size // 8) + (table_size % 8 > 0) # считаем сколько байтов нужно что бы поместить таблицу
        for byte in self.input_file.read(table_bytes):
            fill_deque_from_byte(self.decoding_buffer, byte) # заполняем буффер байтами, которые считали из хедера
        try:
            for _ in range((table_bytes * 8) - table_size):
                self.decoding_buffer.pop() # достаём все лишние биты, которые были считаны
            while len(self.decoding_buffer) > 16:
                byte, cipher_len = (int.from_bytes(bits_to_bytes(deque( # считываем первые 2 элемента, символ в двоич. и длину кода в двоич.
                    self.decoding_buffer.popleft() for _ in range(8)
                )), byteorder='little') for _ in range(2))
                self.coding_table[BitSequence(self.decoding_buffer.popleft() for _ in range(cipher_len))] = byte # создаём последовательность битов и присваиваем ей байт который мы считали, таким образом мы создаём таблицу декодирования 
        except IndexError:
            raise RuntimeError("Incorrect input file")
        self.decoding_buffer.clear() # очищаем буффер
        return trailing_zeros # возвращаем количество ноликов в конце файла

    def _decode(self, data: bytes, skip_last_bits: int = 0) -> None:
        """
        Decodes given bytes to the output file

        :param data: data to decode
        :param skip_last_bits: count of bits to skip in the end of data
        """
        for byte in data:  # load data to the decoding buffer
            fill_deque_from_byte(self.decoding_buffer, byte)
        for _ in range(min(len(self.decoding_buffer), skip_last_bits)):  # skip last bits if needed (no more than buffer size)
            self.decoding_buffer.pop()
        cipher_storage = deque()
        output_buffer = []
        stop = False
        while True:  # this loop will exit by the stop flag
            while BitSequence(cipher_storage, use_given_deque=True) not in self.coding_table:
                # Add new bit to the cipher_storage, search it in the coding table and append a byte
                # to the output_buffer if it was found. Sequence of length more than 256 will cause an exception
                if not self.decoding_buffer:
                    self.decoding_buffer.extend(cipher_storage)
                    stop = True
                    break
                cipher_storage.append(self.decoding_buffer.popleft())
                if len(cipher_storage) > 256:
                    raise RuntimeError(f"Invalid code size (code is {hash(BitSequence(cipher_storage))})")
            if stop:
                break
            output_buffer.append(self.coding_table[BitSequence(cipher_storage, use_given_deque=True)])
            cipher_storage.clear()
        self.output_file.write(bytes(output_buffer))  # Write output_buffer to the output file

    def input_is_eof(self) -> bool:
        """
        Check if we reached the end of file
        """
        return self.input_file.tell() + 1 >= self.input_file_size

    def __call__(self) -> None:
        """
        Decompresses the input file to output one
        """
        trailing_zeros = self.read_header()  # save coding table from the file and return count of zero-bits in the end
        while not self.input_is_eof():
            # read and decode data using the coding table
            buffer = self.input_file.read(INPUT_BUFFER_SIZE)
            is_eof = self.input_is_eof()
            self._decode(buffer, trailing_zeros if is_eof else 0)
            if is_eof:
                return
