from typing import BinaryIO, Deque, Dict
from collections import deque

from utils import fill_deque_from_byte, bits_to_bytes
from huffman_tree import HuffmanTree


INPUT_BUFFER_SIZE = 10240  # bytes
OUTPUT_BUFFER_FLUSH_SIZE = 81920  # bits (weak limitation)


class Encoder:
    def __init__(self, input_file: BinaryIO, output_file: BinaryIO):
        """
        Initializes the instance of encoder without reading or writing any data from/to files
        """
        self.input_file = input_file # инпут файл, который был передан
        self.output_file = output_file # аутпут файл, куда будем писать закодированное сообщение
        self.coding_table = {} # кодирущая таблица, с помощью которой будет проходить кодировка
        self.encoding_buffer = deque() # буффер, в котором будем хранить биты

    def generate_codes(self) -> Dict[int, Deque[bool]]:
        """
        Reads the whole input file and generates coding_table by the Huffman tree

        :return: coding table where key is byte and value is deque of bits
        """
        self.input_file.seek(0) # переключаемся на первый байт входного файла
        freq_table = {} # создаём пустую мапу частот, в котоорую в дальнейшем будем её записывать
        while True:
            input_buffer = self.input_file.read(INPUT_BUFFER_SIZE) # считываем и помещаем данные из инпут файла в буффер (в память)
            if not input_buffer: # если ничего не считалось, т.е. файл пустой - выходим
                break
            for byte in input_buffer: # если считались данные, перебираем каждый байт этого файла
                if byte in freq_table: # если данный байт уже есть в таблице частот, инкрементируем его значение
                    freq_table[byte] += 1
                else: # если данного байта ещё нет в таблице частот, значит нужно его добавить и присвоить 1, как количество повторений
                    freq_table[byte] = 1
        tree = HuffmanTree(freq_table) # строим дерево после формирования таблицы частот (внутри простроится дерево, и вернем коды которые получатся для каждого символа)
        return tree.generate_codes() # возвращаем построенные коды

    def write_header(self) -> int: # записываем хедер
        """
        Writes the coding_table into the output file

        :return: offset of the byte after written table (in file) to start writing data from
        """
        self.output_file.seek(0)
        self.output_file.write(bytes(0 for _ in range(5)))
        table_length_counter = 0  # count of bits in table
        for coding_entry in self.coding_table:
            # writing each coding entry first to buffer and then to file
            fill_deque_from_byte(self.encoding_buffer, coding_entry)
            entry_bit_repr = self.coding_table[coding_entry]
            fill_deque_from_byte(self.encoding_buffer, len(entry_bit_repr))
            self.encoding_buffer.extend(entry_bit_repr)
            table_length_counter += 16 + len(entry_bit_repr)
            if len(self.encoding_buffer) >= OUTPUT_BUFFER_FLUSH_SIZE:
                # write all buffer's full bytes to the file if it is too large
                self.output_file.write(bits_to_bytes(self.encoding_buffer))
        self.output_file.write(bits_to_bytes(self.encoding_buffer, flush=True))  # flush everything left in buffer to the file
        self.output_file.flush()
        curr_pos = self.output_file.tell()
        self.output_file.seek(1)
        self.output_file.write(table_length_counter.to_bytes(4, 'little'))  # write the size of coding table to the output file
        self.output_file.seek(curr_pos)
        return curr_pos # возвращаем позицию с которой начинать записывать зашифрованные данные

    def _encode(self, data: bytes) -> None:
        """
        Encode given bytes to the buffer (flushing it in process if it's too large)

        :param data: bytes to encode
        """
        for byte in data: # считали байты из файла
            self.encoding_buffer.extend(self.coding_table[byte]) # узнаём как шифровать байт и записываем его, используя байт как ключ и вытаскивая биты как значения для этого байта
            if len(self.encoding_buffer) >= OUTPUT_BUFFER_FLUSH_SIZE: # если длина буфера превосходит максимальный размер, то скидываем в файлик, переводя биты в байты
                self.output_file.write(bits_to_bytes(self.encoding_buffer))

    def __call__(self) -> None:
        """
        Generates the coding table, writes it to file, encodes the file by it
        and writes number of trailing zeros to the output file
        """
        self.coding_table = self.generate_codes() # заполняем кодирующую таблицу сгенерированными кодами (при проходе дерева сверху вниз)
        data_start = self.write_header() # узнаём откуда начинать писать данные
        self.output_file.seek(data_start) # переходим в указанную позицию в аутпут файле
        self.input_file.seek(0) # переходим на начало в инпут файле
        self.encoding_buffer.clear() # очищаем буффер
        while len(bytes_to_encode := self.input_file.read(INPUT_BUFFER_SIZE)) != 0: # кодируем баты которые мы читаем из инпут файла
            self._encode(bytes_to_encode)  # encode the file, breaking it down into sections in the process
        trailing_zeros = self.flush() # узнаём сколько нужно добавить нулевых битов, что бы размер был кратен 8
        self.output_file.seek(0) # перемещаемся в нулевую позицию аутпут файла, и записываем количество нулей которое мы посчитали
        self.output_file.write(trailing_zeros.to_bytes(1, 'little'))  # write number if trailing zeros to the start of file

    def flush(self) -> int:
        """
        Flush everything from the buffer to the file

        :return: additional zero bits in the end of file
        """
        result = (8 - (len(self.encoding_buffer) % 8)) % 8
        self.output_file.write(bits_to_bytes(self.encoding_buffer, flush=True))
        return result
