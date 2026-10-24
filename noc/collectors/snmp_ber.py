from __future__ import annotations

import asyncio
import ipaddress
import random
import socket
from dataclasses import dataclass
from typing import Any, Iterable


class BerError(ValueError):
    pass


OID = tuple[int, ...]
GET_REQUEST, GET_NEXT_REQUEST, GET_RESPONSE, GET_BULK_REQUEST = 0xA0, 0xA1, 0xA2, 0xA5
_PDU_TAGS = {GET_REQUEST, GET_NEXT_REQUEST, GET_RESPONSE, GET_BULK_REQUEST}
_UNSIGNED_TAGS = {0x41, 0x42, 0x43, 0x46}
_EXCEPTION_TAGS = {0x80, 0x81, 0x82}


@dataclass(slots=True)
class BerMessage:
    version: int
    community: bytes
    pdu_tag: int
    request_id: int
    error_status: int
    error_index: int
    var_binds: list[tuple[OID, Any]]


def _length(size: int) -> bytes:
    if size < 0:
        raise BerError("Negative BER length")
    if size < 128:
        return bytes((size,))
    encoded = size.to_bytes((size.bit_length() + 7) // 8, "big")
    return bytes((0x80 | len(encoded),)) + encoded


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes((tag,)) + _length(len(content)) + content


def _integer_content(value: int) -> bytes:
    size = 1
    while value < -(1 << (size * 8 - 1)) or value >= (1 << (size * 8 - 1)):
        size += 1
    return value.to_bytes(size, "big", signed=True)


def _integer(value: int) -> bytes:
    return _tlv(0x02, _integer_content(value))


def _base128(value: int) -> bytes:
    if value < 0:
        raise BerError("OID arcs must be non-negative")
    parts = [value & 0x7F]
    value >>= 7
    while value:
        parts.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(parts))


def _oid_tuple(oid: str | Iterable[int]) -> OID:
    try:
        arcs = tuple(int(part) for part in oid.strip(".").split(".")) if isinstance(oid, str) else tuple(int(part) for part in oid)
    except (TypeError, ValueError):
        raise BerError("Invalid object identifier") from None
    if len(arcs) < 2 or arcs[0] not in (0, 1, 2) or arcs[1] < 0 or (arcs[0] < 2 and arcs[1] > 39) or any(arc < 0 for arc in arcs[2:]):
        raise BerError("Invalid object identifier")
    return arcs


def encode_oid(oid: str | Iterable[int]) -> bytes:
    arcs = _oid_tuple(oid)
    content = _base128(arcs[0] * 40 + arcs[1]) + b"".join(_base128(arc) for arc in arcs[2:])
    return _tlv(0x06, content)


def _read_tlv(data: bytes, offset: int = 0) -> tuple[int, bytes, int]:
    if offset + 2 > len(data):
        raise BerError("Truncated BER value")
    tag, first_length = data[offset], data[offset + 1]
    offset += 2
    if first_length & 0x80:
        octets = first_length & 0x7F
        if octets == 0 or octets > 4 or offset + octets > len(data):
            raise BerError("Invalid BER length")
        length = int.from_bytes(data[offset:offset + octets], "big")
        if length < 128:
            raise BerError("Non-minimal BER length")
        offset += octets
    else:
        length = first_length
    end = offset + length
    if end > len(data):
        raise BerError("Truncated BER content")
    return tag, data[offset:end], end


def _decode_base128(content: bytes) -> list[int]:
    arcs: list[int] = []
    value = 0
    open_arc = False
    for octet in content:
        open_arc = bool(octet & 0x80)
        value = (value << 7) | (octet & 0x7F)
        if not open_arc:
            arcs.append(value)
            value = 0
    if open_arc or not arcs:
        raise BerError("Invalid BER object identifier")
    return arcs


def decode_oid(content: bytes) -> OID:
    packed = _decode_base128(content)
    first = packed[0]
    if first < 40:
        arcs = (0, first)
    elif first < 80:
        arcs = (1, first - 40)
    else:
        arcs = (2, first - 80)
    return arcs + tuple(packed[1:])


def _decode_value(tag: int, content: bytes) -> Any:
    if tag == 0x02:
        if not content:
            raise BerError("Empty BER integer")
        return int.from_bytes(content, "big", signed=True)
    if tag in _UNSIGNED_TAGS:
        if not content:
            raise BerError("Empty BER counter")
        return int.from_bytes(content, "big", signed=False)
    if tag == 0x04:
        return content.decode("utf-8", errors="replace")
    if tag == 0x05 or tag in _EXCEPTION_TAGS:
        return None
    if tag == 0x06:
        return ".".join(map(str, decode_oid(content)))
    if tag == 0x40:
        if len(content) != 4:
            raise BerError("Invalid SNMP IPv4 address")
        return str(ipaddress.ip_address(content))
    if tag == 0x44:
        return content.hex()
    return content.hex()


def _encode_value(value: Any) -> bytes:
    if value is None:
        return _tlv(0x05, b"")
    if isinstance(value, int):
        return _integer(value)
    if isinstance(value, bytes):
        return _tlv(0x04, value)
    return _tlv(0x04, str(value).encode("utf-8"))


def encode_message(
    version: int,
    community: str | bytes,
    pdu_tag: int,
    request_id: int,
    var_binds: Iterable[tuple[str | Iterable[int], Any]],
    *,
    error_status: int = 0,
    error_index: int = 0,
) -> bytes:
    if version not in (0, 1) or pdu_tag not in _PDU_TAGS:
        raise BerError("Unsupported SNMP version or PDU")
    community_bytes = community.encode("utf-8") if isinstance(community, str) else community
    bindings = b"".join(_tlv(0x30, encode_oid(oid) + _encode_value(value)) for oid, value in var_binds)
    pdu = _integer(request_id) + _integer(error_status) + _integer(error_index) + _tlv(0x30, bindings)
    return _tlv(0x30, _integer(version) + _tlv(0x04, community_bytes) + _tlv(pdu_tag, pdu))


def decode_message(packet: bytes) -> BerMessage:
    outer_tag, outer, end = _read_tlv(packet)
    if outer_tag != 0x30 or end != len(packet):
        raise BerError("Invalid SNMP message")
    version_tag, version_content, offset = _read_tlv(outer)
    community_tag, community, offset = _read_tlv(outer, offset)
    pdu_tag, pdu, offset = _read_tlv(outer, offset)
    if version_tag != 0x02 or community_tag != 0x04 or pdu_tag not in _PDU_TAGS or offset != len(outer):
        raise BerError("Invalid SNMP message fields")
    version = _decode_value(version_tag, version_content)
    if version not in (0, 1):
        raise BerError("Unsupported SNMP version")

    request_tag, request_content, offset = _read_tlv(pdu)
    status_tag, status_content, offset = _read_tlv(pdu, offset)
    index_tag, index_content, offset = _read_tlv(pdu, offset)
    list_tag, list_content, offset = _read_tlv(pdu, offset)
    if (request_tag, status_tag, index_tag, list_tag) != (0x02, 0x02, 0x02, 0x30) or offset != len(pdu):
        raise BerError("Invalid SNMP PDU")

    var_binds: list[tuple[OID, Any]] = []
    bind_offset = 0
    while bind_offset < len(list_content):
        bind_tag, bind_content, bind_offset = _read_tlv(list_content, bind_offset)
        if bind_tag != 0x30:
            raise BerError("Invalid SNMP variable binding")
        oid_tag, oid_content, item_offset = _read_tlv(bind_content)
        value_tag, value_content, item_offset = _read_tlv(bind_content, item_offset)
        if oid_tag != 0x06 or item_offset != len(bind_content):
            raise BerError("Invalid SNMP variable binding fields")
        var_binds.append((decode_oid(oid_content), _decode_value(value_tag, value_content)))

    return BerMessage(
        version=version,
        community=community,
        pdu_tag=pdu_tag,
        request_id=_decode_value(request_tag, request_content),
        error_status=_decode_value(status_tag, status_content),
        error_index=_decode_value(index_tag, index_content),
        var_binds=var_binds,
    )


class SNMPBerClient:
    def __init__(self, host: str, version: str, community: str = "public", port: int = 161, timeout: float = 2, retries: int = 1):
        if version not in ("1", "2c"):
            raise ValueError("The BER client supports SNMP v1 and v2c")
        self.host = host
        self.version = 0 if version == "1" else 1
        self.community = community
        self.port = port
        self.timeout = timeout
        self.retries = retries

    def _request_sync(self, pdu_tag: int, oids: list[OID], max_repetitions: int = 0) -> BerMessage:
        request_id = random.randrange(1, 0x7FFFFFFF)
        values = [(oid, None) for oid in oids]
        if pdu_tag == GET_BULK_REQUEST:
            packet = _tlv(0x30, _integer(self.version) + _tlv(0x04, self.community.encode()) + _tlv(
                pdu_tag, _integer(request_id) + _integer(0) + _integer(max_repetitions) +
                _tlv(0x30, b"".join(_tlv(0x30, encode_oid(oid) + _tlv(0x05, b"")) for oid in oids))
            ))
        else:
            packet = encode_message(self.version, self.community, pdu_tag, request_id, values)

        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_DGRAM)
        if not addresses:
            raise BerError(f"Could not resolve SNMP host {self.host}")
        family, socktype, protocol, _, address = addresses[0]
        for _ in range(self.retries + 1):
            try:
                with socket.socket(family, socktype, protocol) as sock:
                    sock.settimeout(self.timeout)
                    sock.connect(address)
                    sock.send(packet)
                    response = decode_message(sock.recv(65535))
                if response.request_id != request_id or response.version != self.version or response.community != self.community.encode():
                    raise BerError("SNMP response does not match the request")
                if response.pdu_tag != GET_RESPONSE:
                    raise BerError("Expected an SNMP GetResponse PDU")
                return response
            except socket.timeout:
                continue
        raise BerError(f"SNMP request timed out for {self.host}:{self.port}")

    async def _request(self, pdu_tag: int, oids: list[OID], max_repetitions: int = 0) -> BerMessage:
        return await asyncio.to_thread(self._request_sync, pdu_tag, oids, max_repetitions)

    async def get(self, oid: str) -> Any | None:
        response = await self._request(GET_REQUEST, [_oid_tuple(oid)])
        if response.error_status == 2:
            return None
        if response.error_status:
            raise BerError(f"SNMP agent returned error status {response.error_status}")
        return response.var_binds[0][1] if response.var_binds else None

    async def walk(self, root_oid: str, max_entries: int = 5000) -> dict[OID, Any]:
        root = _oid_tuple(root_oid)
        cursor = root
        result: dict[OID, Any] = {}
        pdu_tag = GET_NEXT_REQUEST if self.version == 0 else GET_BULK_REQUEST
        while len(result) < max_entries:
            response = await self._request(pdu_tag, [cursor], 20)
            if response.error_status == 2:
                break
            if response.error_status:
                raise BerError(f"SNMP agent returned error status {response.error_status}")
            if not response.var_binds:
                break
            finished = False
            for oid, value in response.var_binds:
                if value is None or oid <= cursor or oid[:len(root)] != root:
                    finished = True
                    break
                result[oid[len(root):]] = value
                cursor = oid
                if len(result) >= max_entries:
                    finished = True
                    break
            if finished:
                break
        return result
