import math
from decimal import Decimal

import pytest

from vyper.exceptions import InvalidLiteral, TypeMismatch


@pytest.mark.parametrize("inp", [1, -1, 2 ** 127 - 1, -(2 ** 127)])
def test_convert_from_int128(get_contract_with_gas_estimation, inp):
    code = f"""
a: int128
b: decimal

@external
def int128_to_decimal(inp: int128) -> (decimal, decimal, decimal):
    self.a = inp
    memory: decimal = convert(inp, decimal)
    storage: decimal = convert(self.a, decimal)
    literal: decimal = convert({inp}, decimal)
    return  memory, storage, literal
"""
    c = get_contract_with_gas_estimation(code)
    assert c.int128_to_decimal(inp) == [Decimal(inp)] * 3


def test_convert_from_uint256(assert_tx_failed, get_contract_with_gas_estimation):
    code = """
@external
def test_variable() -> bool:
    a: uint256 = 1000
    return convert(a, decimal) == 1000.0

@external
def test_passed_variable(a: uint256) -> decimal:
    return convert(a, decimal)
    """

    c = get_contract_with_gas_estimation(code)

    assert c.test_variable() is True
    assert c.test_passed_variable(256) == 256

    max_decimal = math.floor(Decimal(2 ** 167 - 1) / 10 ** 10)
    assert c.test_passed_variable(max_decimal) == Decimal(max_decimal)

    failing_decimal = max_decimal + 1
    assert_tx_failed(lambda: c.test_passed_variable(failing_decimal))


def test_convert_from_uint256_overflow(get_contract_with_gas_estimation, assert_compile_failed):
    code = """
@external
def foo() -> decimal:
    return convert(2**167, decimal)
    """

    assert_compile_failed(lambda: get_contract_with_gas_estimation(code), InvalidLiteral)


def test_convert_from_bool(get_contract_with_gas_estimation):
    code = """
@external
def foo(bar: bool) -> decimal:
    return convert(bar, decimal)
    """

    c = get_contract_with_gas_estimation(code)
    assert c.foo(False) == 0.0
    assert c.foo(True) == 1.0


def test_convert_from_bytes32(get_contract_with_gas_estimation):
    code = """
@external
def foo(bar: bytes32) -> decimal:
    return convert(bar, decimal)
    """

    c = get_contract_with_gas_estimation(code)
    assert c.foo(b"\x00" * 32) == 0.0
    assert c.foo(b"\xff" * 32) == Decimal("-1e-10")
    assert c.foo((b"\x00" * 31) + b"\x01") == Decimal("1e-10")
    assert c.foo((b"\x00" * 30) + b"\x01\x00") == Decimal("256e-10")


def test_convert_from_bytes32_overflow(get_contract_with_gas_estimation, assert_compile_failed):
    # bytes for 2**167
    failing_decimal_bytes = "0x" + (2 ** 167).to_bytes(32, byteorder="big").hex()
    code = f"""
@external
def foo() -> decimal:
    return convert({failing_decimal_bytes}, decimal)
    """

    assert_compile_failed(lambda: get_contract_with_gas_estimation(code), InvalidLiteral)


def test_convert_from_bytes(get_contract_with_gas_estimation):
    code = """
@external
def foo(bar: Bytes[5]) -> decimal:
    return convert(bar, decimal)

@external
def goo(bar: Bytes[16]) -> decimal:
    return convert(bar, decimal)
    """

    c = get_contract_with_gas_estimation(code)

    assert c.foo(b"\x00\x00\x00\x00\x00") == 0.0
    assert c.foo(b"\x00\x07\x5B\xCD\x15") == Decimal("123456789e-10")

    assert c.goo(b"") == 0.0
    assert c.goo(b"\x00") == 0.0
    assert c.goo(b"\x01") == Decimal("1e-10")
    assert c.goo(b"\x00\x01") == Decimal("1e-10")
    assert c.goo(b"\x01\x00") == Decimal("256e-10")
    assert c.goo(b"\x01\x00\x00\x00\x01") == Decimal("4294967297e-10")
    assert c.goo(b"\xff" * 16) == Decimal("-1.0e-10")


def test_convert_from_too_many_bytes(get_contract_with_gas_estimation, assert_compile_failed):
    code = """
@external
def foo(bar: Bytes[33]) -> decimal:
    return convert(bar, decimal)
    """

    assert_compile_failed(
        lambda: get_contract_with_gas_estimation(code),
        TypeMismatch,
    )

    code = """
@external
def foobar() -> decimal:
    barfoo: Bytes[63] = b"Hello darkness, my old friend I've come to talk with you again."
    return convert(barfoo, decimal)
    """

    assert_compile_failed(
        lambda: get_contract_with_gas_estimation(code),
        TypeMismatch,
    )


def test_convert_from_address(get_contract, assert_compile_failed):
    codes = [
        """
stor: address
@external
def conv_zero_stor() -> decimal:
    self.stor = ZERO_ADDRESS
    return convert(self.stor, decimal)
""",
        """
@external
def conv(param: address) -> decimal:
    return convert(param, decimal)
""",
        """
@external
def conv_zero_literal() -> decimal:
    return convert(ZERO_ADDRESS, decimal)
""",
        """
@external
def conv_neg1_literal() -> decimal:
    return convert(0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF, decimal)
""",
    ]
    for c in codes:
        assert_compile_failed(lambda: get_contract(c), TypeMismatch)


def test_convert_from_int256(get_contract_with_gas_estimation, assert_tx_failed):
    code = """
@external
def test(foo: int256) -> decimal:
    return convert(foo, decimal)
    """

    c = get_contract_with_gas_estimation(code)
    assert c.test(0) == 0
    assert c.test(-1) == -1
    assert_tx_failed(lambda: c.test(2 ** 255 - 1))
    assert_tx_failed(lambda: c.test(-(2 ** 255)))

    max_decimal = math.floor(Decimal(2 ** 167 - 1) / 10 ** 10)
    assert c.test(max_decimal) == Decimal(max_decimal)

    min_decimal = math.ceil(-Decimal(2 ** 167) / 10 ** 10)
    assert c.test(min_decimal) == Decimal(min_decimal)

    assert_tx_failed(lambda: c.test(max_decimal + 1))
    assert_tx_failed(lambda: c.test(min_decimal - 1))
