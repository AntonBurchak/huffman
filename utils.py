from typing import Deque


def fill_deque_from_byte(destination: Deque[bool], source: int) -> None:
    """
    Copies bits from the given byte to the end of given deque

    :param destination: deque to fill
    :param source: byte to use. If it more than 256, it will use remainder of its division by 256
    """
    source &= 0xff
    bin_repr = bin(source)[2:]
    for _ in range(8 - len(bin_repr)):
        destination.append(False)
    for bit in bin_repr:
        destination.append(bit == '1')


def bits_to_bytes(source: Deque[bool], flush: bool = False) -> bytes:
    """
    if flush:
        Removes everything from source,
        makes bytes from its bits,
        fills trailing space with zeros (if len(source) % 8 != 0)
        and returns these bytes
    else:
        Removes n*8 bits from source,
        makes bytes from them and returns
    """
    result = []
    while ((bits_left := len(source)) >= 8) or (flush and source):
        tmp_byte = 0
        for _ in range(min(bits_left, 8)):
            tmp_byte <<= 1
            tmp_byte |= int(source.popleft())
        if bits_left < 8:
            tmp_byte <<= 8 - bits_left
        result.append(tmp_byte)
    print(bytes(result));
    return bytes(result)
