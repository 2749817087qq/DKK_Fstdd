"""opt-in 安全档：cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256 混合加密（C4 / REQ-004）。

载荷结构（``FSTDDEXP1`` 混合封包）::

    MAGIC(9) | algo(1) | RSA-OAEP 包裹的 AES-256 密钥(384) | IV(16) | CT(n) | HMAC-SHA256(32)

- RSA-3072 OAEP-SHA256 的明文上限是 **318 字节** ⇒ 不能直加密文，必须混合加密（SC-018）。
- OAEP 必须**显式** ``rsa_oaep_md:sha256`` **且** ``rsa_mgf1_md:sha256``；省略 MGF1 会退化为
  sha1 导致解密失败（SC-017，来自 cred-relay ``selftest.sh`` T3b 实测）。
- 正文层 AEAD：本运行环境的 ``openssl enc`` **不支持 AEAD(GCM)**（``enc: AEAD ciphers not
  supported``），且 ``cryptography`` 库不可用 ⇒ 采用 **AES-256-CTR + HMAC-SHA256**
  （encrypt-then-MAC，MAC 覆盖 ``header||CT``）的等价 AEAD 构造。详见 design-adjustments（Major）。

所有出站载荷在调用方**先脱敏**（出站不变量），本模块只负责机密性 + 完整性。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import subprocess
from pathlib import Path

MAGIC = b"FSTDDEXP1"
ALGO_CTR_HMAC = 0x01

RSA_WRAP_LEN = 384      # RSA-3072 模长 = 384 字节
IV_LEN = 16             # AES 块长
MAC_LEN = 32            # HMAC-SHA256
AES_KEY_LEN = 32        # AES-256
HEADER_LEN = len(MAGIC) + 1

_MAC_INFO = b"fstdd-exp-mac-v1"


class CryptoError(Exception):
    """安全档加解密失败（密钥缺失/参数不匹配/完整性校验失败）。"""


def default_key_dir(project_root: Path | None = None) -> Path:
    """cred-relay 密钥目录：``$FSTDD_CRED_RELAY_DIR`` 优先，否则 ``<root>/.secrets/cred-relay``。"""
    env = os.environ.get("FSTDD_CRED_RELAY_DIR")
    if env:
        return Path(env)
    root = Path(project_root) if project_root else Path.cwd()
    return root / ".secrets" / "cred-relay"


def default_key_paths(project_root: Path | None = None) -> tuple[Path, Path]:
    d = default_key_dir(project_root)
    return d / "k_pub.pem", d / "k_priv.pem"


def keys_present(pub_path, priv_path) -> bool:
    """两个密钥文件是否都在。开放档下返回 False ⇒ 调用方走明文路径（SC-019）。"""
    try:
        return Path(pub_path).is_file() and Path(priv_path).is_file()
    except OSError:
        return False


def _openssl(args: list, data: bytes) -> bytes:
    try:
        proc = subprocess.run(["openssl", *args], input=data,
                              capture_output=True, check=False)
    except FileNotFoundError as exc:  # pragma: no cover - 依赖环境
        raise CryptoError("openssl 不可用，无法执行安全档加解密") from exc
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise CryptoError(f"openssl 失败: {err}")
    return proc.stdout


def _rsa_wrap(aes_key: bytes, pub_path) -> bytes:
    if not Path(pub_path).is_file():
        raise CryptoError(f"公钥不存在: {pub_path}")
    out = _openssl([
        "pkeyutl", "-encrypt", "-pubin", "-inkey", str(pub_path),
        "-pkeyopt", "rsa_padding_mode:oaep",
        "-pkeyopt", "rsa_oaep_md:sha256",
        "-pkeyopt", "rsa_mgf1_md:sha256",
    ], aes_key)
    if len(out) != RSA_WRAP_LEN:
        raise CryptoError(f"RSA 包裹长度异常: {len(out)} != {RSA_WRAP_LEN}")
    return out


def _rsa_unwrap(wrapped: bytes, priv_path) -> bytes:
    if not Path(priv_path).is_file():
        raise CryptoError(f"私钥不存在: {priv_path}")
    return _openssl([
        "pkeyutl", "-decrypt", "-inkey", str(priv_path),
        "-pkeyopt", "rsa_padding_mode:oaep",
        "-pkeyopt", "rsa_oaep_md:sha256",
        "-pkeyopt", "rsa_mgf1_md:sha256",
    ], wrapped)


def _mac_key(aes_key: bytes) -> bytes:
    return hmac.new(aes_key, _MAC_INFO, hashlib.sha256).digest()


def _compute_mac(mac_key: bytes, header: bytes, ciphertext: bytes) -> bytes:
    return hmac.new(mac_key, header + ciphertext, hashlib.sha256).digest()


def hybrid_encrypt(plaintext: bytes, pub_path) -> bytes:
    """混合加密：RSA-OAEP 包裹随机 AES-256 密钥 + AES-256-CTR + HMAC-SHA256。"""
    aes_key = os.urandom(AES_KEY_LEN)
    iv = os.urandom(IV_LEN)
    wrapped = _rsa_wrap(aes_key, pub_path)
    ct = _openssl([
        "enc", "-aes-256-ctr", "-K", aes_key.hex(), "-iv", iv.hex(),
    ], plaintext)
    header = MAGIC + bytes([ALGO_CTR_HMAC]) + wrapped + iv
    mac = _compute_mac(_mac_key(aes_key), header, ct)
    return header + ct + mac


def _split_blob(blob: bytes):
    """拆包 → (header, wrapped_key, iv, ciphertext, mac)。"""
    if len(blob) < HEADER_LEN + RSA_WRAP_LEN + IV_LEN + MAC_LEN:
        raise CryptoError("封包过短，无法解析")
    if blob[:len(MAGIC)] != MAGIC:
        raise CryptoError("封包 magic 不匹配（非 FSTDD 安全档载荷）")
    algo = blob[len(MAGIC)]
    if algo != ALGO_CTR_HMAC:
        raise CryptoError(f"不支持的算法标识: {algo}")
    off = HEADER_LEN
    wrapped = blob[off:off + RSA_WRAP_LEN]
    off += RSA_WRAP_LEN
    iv = blob[off:off + IV_LEN]
    off += IV_LEN
    ct = blob[off:-MAC_LEN]
    mac = blob[-MAC_LEN:]
    return blob[:off], wrapped, iv, ct, mac


def hybrid_decrypt(blob: bytes, priv_path) -> bytes:
    """解密混合封包；先验完整性（encrypt-then-MAC），再解 RSA，再解正文。"""
    header, wrapped, iv, ct, mac = _split_blob(blob)
    aes_key = _rsa_unwrap(wrapped, priv_path)
    expected = _compute_mac(_mac_key(aes_key), header, ct)
    if not hmac.compare_digest(expected, mac):
        raise CryptoError("完整性校验失败（HMAC 不匹配）")
    return _openssl([
        "enc", "-d", "-aes-256-ctr", "-K", aes_key.hex(), "-iv", iv.hex(),
    ], ct)
