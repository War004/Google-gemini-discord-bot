import math
import mmh3
from bitarray import bitarray

class BloomFilter:
    def __init__(self, expected_items: int, false_positive_rate: float):
        """
        Initializes the Bloom filter with the optimal array size and hash count.
        """
        # Calculate optimal array size (m)
        self.size = self._get_size(expected_items, false_positive_rate)
        
        # Calculate optimal number of hash functions (k)
        self.hash_count = self._get_hash_count(self.size, expected_items)
        
        # Create the bit array and set all bits to 0
        self.bit_array = bitarray(self.size)
        self.bit_array.setall(0)

    def _get_size(self, n: int, p: float) -> int:
        """Calculates m = -(n * ln(p)) / (ln(2)^2)"""
        m = -(n * math.log(p)) / (math.log(2)**2)
        return int(m)

    def _get_hash_count(self, m: int, n: int) -> int:
        """Calculates k = (m / n) * ln(2)"""
        k = (m / n) * math.log(2)
        return int(k)

    def add(self, item: str):
        """Hashes the item k times and sets the corresponding bits to 1."""
        for i in range(self.hash_count):
            # We use 'i' as the seed for mmh3 so each hash function is unique
            index = mmh3.hash(str(item), i) % self.size
            self.bit_array[index] = 1

    def check(self, item: str) -> bool:
        """Returns True if the item is probably in the filter, False if definitely not."""
        for i in range(self.hash_count):
            index = mmh3.hash(str(item), i) % self.size
            # If any bit is 0, the item is definitely not in the filter
            if self.bit_array[index] == 0:
                return False
        
        # If all checked bits are 1, the item is probably in the filter
        return True