import asyncio
import socket
import threading

import pytest

from noc.collectors import snmp_ber
from noc.collectors.snmp_ber import (
    BerError,
    GET_BULK_REQUEST,
    GET_NEXT_REQUEST,
    GET_REQUEST,
    GET_RESPONSE,
    SNMPBerClient,
    decode_message,
    decode_oid,
    encode_message,
    encode_oid,
)


OID = "1.3.6.1.2.1.25.3.3.1.2"


def test_get_request_round_trip_and_oid_packing():
    request = decode_message(encode_message(1, "public", GET_REQUEST, 77, [(OID, None)]))
    assert request.version == 1
    assert request.community == b"public"
    assert request.pdu_tag == GET_REQUEST
    assert request.request_id == 77
    assert request.var_binds == [((1, 3, 6, 1, 2, 1, 25, 3, 3, 1, 2), None)]
    tag, content, end = snmp_ber._read_tlv(encode_oid(OID))
    assert tag == 0x06 and end == len(encode_oid(OID))
    assert decode_oid(content) == request.var_binds[0][0]


def test_response_round_trip_and_counter64_decode():
    request_id = 1024
    packet = encode_message(1, b"public", GET_RESPONSE, request_id, [(OID, 30_000_000_000)])
    response = decode_message(packet)
    assert response.pdu_tag == GET_RESPONSE
    assert response.request_id == request_id
    assert response.var_binds[0][1] == 30_000_000_000
    assert snmp_ber._decode_value(0x46, (1 << 63 | 123).to_bytes(8, "big")) == (1 << 63 | 123)


def test_decoder_rejects_truncated_packet():
    with pytest.raises(BerError):
        decode_message(b"\x30\x05\x02")


def test_udp_get_uses_loopback_responder():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    server.settimeout(2)
    port = server.getsockname()[1]
    errors = []

    def respond():
        try:
            packet, address = server.recvfrom(65535)
            request = decode_message(packet)
            response = encode_message(request.version, request.community, GET_RESPONSE, request.request_id, [(request.var_binds[0][0], 123)])
            server.sendto(response, address)
        except Exception as error:
            errors.append(error)
        finally:
            server.close()

    worker = threading.Thread(target=respond, daemon=True)
    worker.start()
    value = asyncio.run(SNMPBerClient("127.0.0.1", "2c", port=port, timeout=1).get(OID))
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert not errors
    assert value == 123


@pytest.mark.parametrize(("version", "expected_pdu"), [("1", GET_NEXT_REQUEST), ("2c", GET_BULK_REQUEST)])
def test_walk_stops_at_subtree_boundary(version, expected_pdu):
    root = (1, 3, 6, 1, 2, 1, 1)
    outside = (1, 3, 6, 1, 2, 1, 2, 1)
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    server.settimeout(2)
    port = server.getsockname()[1]
    errors = []

    def respond():
        try:
            for index in range(2):
                packet, address = server.recvfrom(65535)
                request = decode_message(packet)
                assert request.pdu_tag == expected_pdu
                if index == 0 and version == "2c":
                    bindings = [(root + (1,), 7), (root + (2,), "device")]
                elif index == 0:
                    bindings = [(root + (1,), 7)]
                elif version == "2c":
                    bindings = [(outside, 0)]
                else:
                    bindings = [(outside, 0)]
                server.sendto(encode_message(request.version, request.community, GET_RESPONSE, request.request_id, bindings), address)
        except Exception as error:
            errors.append(error)
        finally:
            server.close()

    worker = threading.Thread(target=respond, daemon=True)
    worker.start()
    values = asyncio.run(SNMPBerClient("127.0.0.1", version, port=port, timeout=1).walk(".".join(map(str, root))))
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert not errors
    if version == "2c":
        assert values == {(1,): 7, (2,): "device"}
    else:
        assert values == {(1,): 7}
