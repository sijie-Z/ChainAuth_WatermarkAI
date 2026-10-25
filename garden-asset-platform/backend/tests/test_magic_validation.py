"""文件魔数校验：覆盖常见误杀与漏检场景"""
import io

from app.resources.asset import validate_magic_bytes


def _file(data):
    return io.BytesIO(data)


def test_empty_file_is_rejected():
    assert validate_magic_bytes(_file(b''), 'png') is False
    assert validate_magic_bytes(_file(b''), 'docx') is False


def test_mp4_variants_are_accepted():
    for brand in (b'isom', b'mp41', b'mp42', b'avc1', b'M4V '):
        data = b'\x00\x00\x00\x18ftyp' + brand + b'\x00' * 32
        assert validate_magic_bytes(_file(data), 'mp4') is True


def test_mov_requires_qt_brand():
    assert validate_magic_bytes(
        _file(b'\x00\x00\x00\x14ftypqt  ' + b'\x00' * 32), 'mov'
    ) is True
    assert validate_magic_bytes(
        _file(b'\x00\x00\x00\x18ftypisom' + b'\x00' * 32), 'mov'
    ) is False


def test_office_and_cad_documents():
    ole = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 32
    assert validate_magic_bytes(_file(ole), 'doc') is True
    assert validate_magic_bytes(_file(ole), 'xls') is True
    assert validate_magic_bytes(_file(b'PK\x03\x04' + b'\x00' * 32), 'docx') is True
    assert validate_magic_bytes(
        _file(b'AC1027' + b'\x00' * 32), 'dwg'
    ) is True
    assert validate_magic_bytes(
        _file(b'0\r\nSECTION\r\n2\r\nHEADER\r\n'), 'dxf'
    ) is True


def test_binary_stl_and_text_formats():
    assert validate_magic_bytes(_file(b'\x00' * 84), 'stl') is True
    assert validate_magic_bytes(_file(b'solid cube\nfacet normal 0 0 1'), 'stl') is True
    assert validate_magic_bytes(_file(b'{"type":"FeatureCollection"}'), 'geojson') is True
    assert validate_magic_bytes(_file(b'v 0 0 0\nf 1 2 3\n'), 'obj') is True
    assert validate_magic_bytes(_file(b'not really an object'), 'obj') is False


def test_renamed_containers_are_rejected():
    # RIFF 容器必须同时匹配子类型，不能把 AVI 改名成 WebP
    assert validate_magic_bytes(
        _file(b'RIFF\x00\x00\x00\x00AVI LIST' + b'\x00' * 32), 'webp'
    ) is False
    assert validate_magic_bytes(
        _file(b'RIFF\x00\x00\x00\x00WEBPVP8 ' + b'\x00' * 32), 'webp'
    ) is True
    assert validate_magic_bytes(
        _file(b'BMW something'), 'bmp'
    ) is True
    assert validate_magic_bytes(_file(b'PK\x05\x06' + b'\x00' * 18), 'zip') is True
