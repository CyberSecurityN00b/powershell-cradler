"""
MADE WITH CLAUDE
Reproduces PowerShell's Get-Random functionality in Python.

Architecture (why this is non-obvious):
    PowerShell wraps System.Random in its own PolymorphicRandomNumberGenerator class.
    That wrapper's Next() calls System.Random.NextBytes(byte[4]), which internally
    calls the legacy subtractive InternalSample() once per byte (4 calls total),
    then reinterprets the 4 bytes as a little-endian int32 via BitConverter.ToInt32.
    The result is adjusted (retry if == int.MaxValue, add int.MaxValue if negative),
    then scaled to the requested range.

    This means each logical random number consumes 4 legacy PRNG samples, not 1.
"""

import random as _py_random
import struct

from typing import List

_MBIG  = 2147483647 # int.MaxValue
_MSEED = 161803398

class DotNetRandom:
    """
    Replicates System.Random(int seed) - the legacy .NET subtractive PRNG.
    Provides both the raw legacy InternalSample() and the PolymorphicRNG-style
    Next() that PowerShell's Get-Random actually calls.
    """

    def __init__(self, seed: int):
        self._seed_array = [0] * 56
        self._inext = 0
        self._inextp = 21

        subtraction = _MBIG if seed == -2147483648 else abs(seed)
        mj = _MSEED - subtraction
        self._seed_array[55] = mj
        mk = 1

        ii = 0
        for i in range(1,55):
            if (ii := ii + 21) >= 55:
                ii -= 55
            self._seed_array[ii] = mk
            mk = mj - mk
            if mk < 0:
                mk += _MBIG
            mj = self._seed_array[ii]

        for _ in range(1,5):
            for i in range(1,56):
                n = i + 30
                if n >= 55:
                    n-= 55
                val = self._seed_array[i] - self._seed_array[1 + n]
                val = (val & 0xFFFFFFFF) - 0x100000000 if (val & 0xFFFFFFFF) >= 0x80000000 else (val & 0xFFFFFFFF)
                if val < 0:
                    val += _MBIG
                self._seed_array[i] = val

    def _legacy_internal_sample(self) -> int:
        """System.Random.InternalSample() - the raw subtractive PRNG output."""
        loc_inext = self._inext + 1
        if loc_inext >= 56:
            loc_inext = 1

        loc_inextp = self._inextp + 1
        if loc_inextp >= 56:
            loc_inextp = 1

        ret_val = self._seed_array[loc_inext] - self._seed_array[loc_inextp]

        if ret_val == _MBIG:
            ret_val -= 1
        if ret_val < 0:
            ret_val += _MBIG

        self._seed_array[loc_inext] = ret_val
        self._inext = loc_inext
        self._inextp = loc_inextp

        return ret_val
    
    def _next_bytes(self, count: int) -> bytes:
        """System.Random.NextBytes - each byte is InternalSample() % 256"""
        return bytes(self._legacy_internal_sample() % 256 for _ in range(count))
    
    def _poly_next(self) -> int:
        """
        PolymorphicRandomNumberGenerator.Next().
        Calls NextBytes(40), interprets as little-endian int32, adjusts sign.
        Consumes exactly 4 legacy InternalSample() calls per invocation (unless
        the extremely rare int.MaxValue retry occurs).
        """
        while True:
            n = struct.unpack('<i', self._next_bytes(4))[0]
            if n != _MBIG:
                break
        if n < 0:
            n += _MBIG
        return n
    
    def next(self, min_value: int, max_value: int) -> int:
        """
        PolymorphicRandomNumberGenerator.Next(minValue, maxValue).
        Equivalent to PowerShell's Generator.Next(min, max).
        """
        range_val = max_value - min_value
        if range_val <= _MBIG:
            return int(self._poly_next() * (1.0 / _MBIG) * range_val) + min_value
        raise ValueError(f"Range {range_val} exceeds int.MaxValue; large-range path not implemented")
    
    def next_max(self, max_value: int) -> int:
        """PolymorphicRandomNumberGenerator.Next(maxValue) - Same as Next(0, maxValue)."""
        return self.next(0, max_value)
    
def powershell_get_random_count(items: list, seed: int, count: int) -> list:
    """
    Reproduces: $items | Get-Random -SetSeed $seed -Count $count

    PowerShell's GetRandomCommandBase uses two phases:
        1. Reservoir sampling (Knuth Algorithm R) as items arrive in ProcessRecord
        2. Forward Fisher-Yates shuffle of the reservoir in EndProcessing

    Works for all PowerShell verions that support -Count with piped input.
    """
    rng = DotNetRandom(seed)
    items = list(items)
    n = len(items)
    count = min(count, n)

    # Phase 1: reservoir sampling
    reservoir = list(items[:count])
    for i, item in enumerate(items[count:], start=count):
        if rng.next_max(i + 1) < count:
            reservoir[rng.next_max(count)] = item

    # Phase 2: forward Fisher-Yates shuffle of the reservoir
    k = len(reservoir)
    result = []
    for i in range(k):
        j = rng.next(i,k)
        result.append(reservoir[j])
        if i != j:
            reservoir[j] = reservoir[i]

    return result


powershell_avoid_strings = [
    "amsi"
]

def get_random_obfuscated_string(string: str, seed: int = None, list_avoid_strings: List[str] = powershell_avoid_strings) -> str:
    while True:
        if seed is None:
            seed = _py_random.randint(0, 2147483646)

        n = len(string)

        shuffled = powershell_get_random_count(list(range(n)), seed, n)

        unshuffled = [''] * n
        for i, dest in enumerate(shuffled):
            unshuffled[dest] = string[i]
        unshuffled_str = ''.join(unshuffled)

        regenerate = False
        for avoid in list_avoid_strings:
            if avoid.casefold() in unshuffled_str.casefold():
                seed = None
                regenerate = True

        if not regenerate:
            break

    return f'([string]::new(([char[]]"{unshuffled_str.replace('"','`"').replace("$","`$")}"|Get-Random -Se {seed} -C {n})))'