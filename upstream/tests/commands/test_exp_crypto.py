"""Slice 3 契约测试：opt-in 安全档混合加密（C4 / REQ-004，TC-ESEC-001..005）。

对应 spec：
- SC-015 出站前先脱敏、再混合加密（RSA-OAEP 包裹随机 AES 密钥 + AEAD 正文）
- SC-016 round-trip 逐字节一致
- SC-017 OAEP 参数必须显式 rsa_oaep_md:sha256 + rsa_mgf1_md:sha256
- SC-018 正文 > 318B 仍走混合加密（RSA 只包裹 AES 密钥）
- SC-019 未启用 --secure 且无密钥时不依赖任何密钥（开放档）

⚠️ 设计偏离（见 design-adjustments）：运行环境 `openssl enc` 不支持 AEAD(GCM)，
`cryptography` 库不可用 ⇒ 正文层用 AES-256-CTR + HMAC-SHA256（encrypt-then-MAC）
等价 AEAD 构造；RSA-OAEP-SHA256 包裹 AES 密钥的混合结构不变。
"""
import subprocess

import pytest


@pytest.fixture(scope="module")
def keypair(tmp_path_factory):
    """生成一次性 RSA-3072 密钥对（openssl CLI）。"""
    d = tmp_path_factory.mktemp("credrelay")
    priv, pub = d / "k_priv.pem", d / "k_pub.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA",
                    "-pkeyopt", "rsa_keygen_bits:3072", "-out", str(priv)],
                   check=True, capture_output=True)
    subprocess.run(["openssl", "rsa", "-in", str(priv), "-pubout", "-out", str(pub)],
                   check=True, capture_output=True)
    return pub, priv


def _mod():
    from fstdd.cli.commands import _exp_crypto as m
    return m


def test_esec001_encrypt_hides_plaintext(tmp_path, keypair):
    """TC-ESEC-001 / SC-015：加密后出站载荷不含明文（脱敏后加密）。"""
    pub, _ = keypair
    plaintext = b"FSTDD-EXP secret payload 2026-10-11"
    blob = _mod().hybrid_encrypt(plaintext, pub)
    assert isinstance(blob, bytes)
    assert plaintext not in blob
    assert len(blob) > len(plaintext)


def test_esec002_roundtrip_byte_identical(keypair):
    """TC-ESEC-002 / SC-016：加密→解密逐字节一致。"""
    pub, priv = keypair
    for payload in (b"", b"short", bytes(range(256)), "中文载荷".encode()):
        blob = _mod().hybrid_encrypt(payload, pub)
        assert _mod().hybrid_decrypt(blob, priv) == payload


def test_esec003_oaep_params_locked(keypair):
    """TC-ESEC-003 / SC-017：OAEP 摘要参数锁定 —— 参数不匹配必须解不开。

    实测（openssl 3.5.7）：省略 ``rsa_mgf1_md`` 时 MGF1 默认**跟随** ``rsa_oaep_md``（不再退化为
    sha1），故以「sha1 OAEP 解密必须失败」作为参数锁定的判据（对应 cred-relay selftest T3a）。
    我们自身仍**显式**指定 sha256 + MGF1 sha256（跨版本互操作防御）。
    """
    pub, priv = keypair
    m = _mod()
    blob = m.hybrid_encrypt(b"param-lock-probe", pub)
    wrapped = m._split_blob(blob)[1]  # RSA 包裹的 AES 密钥

    # 正例：显式 sha256 + mgf1 sha256 可解
    ok = subprocess.run(
        ["openssl", "pkeyutl", "-decrypt", "-inkey", str(priv),
         "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256",
         "-pkeyopt", "rsa_mgf1_md:sha256"],
        check=False, input=wrapped, capture_output=True)
    assert ok.returncode == 0

    # 反例：sha1 OAEP 摘要必须失败（参数锁定生效）
    bad = subprocess.run(
        ["openssl", "pkeyutl", "-decrypt", "-inkey", str(priv),
         "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha1",
         "-pkeyopt", "rsa_mgf1_md:sha1"],
        check=False, input=wrapped, capture_output=True)
    assert bad.returncode != 0


def test_esec004_long_payload_uses_hybrid(keypair):
    """TC-ESEC-004 / SC-018：正文 > 318B 仍可加解密（RSA 只包裹 AES 密钥）。"""
    pub, priv = keypair
    payload = b"X" * 4096  # 远超 RSA-3072 OAEP 的 318B 上限
    blob = _mod().hybrid_encrypt(payload, pub)
    assert _mod().hybrid_decrypt(blob, priv) == payload


def test_esec005_no_keys_open_mode(tmp_path):
    """TC-ESEC-005 / SC-019：无密钥 → keys_present=False 且加密给出明确错误（开放档不依赖密钥）。"""
    m = _mod()
    pub = tmp_path / "nope_pub.pem"
    priv = tmp_path / "nope_priv.pem"
    assert m.keys_present(pub, priv) is False
    with pytest.raises(m.CryptoError):
        m.hybrid_encrypt(b"x", pub)
