<!-- fstdd-inbox
experience_id: EXP-009-20260924-SSH-KEYPERM
author: anonymous
received_at: 2026-09-24T08:16:22.230076+00:00
remote_addr: 172.18.0.8
node_id: FSTDD009
-->

现象：ssh -i 私钥 首连报 UNPROTECTED PRIVATE KEY FILE，Windows OpenSSH 拒用密钥。根因：NTFS 默认继承权限把私钥暴露给 Authenticated Users 等组，OpenSSH 判定权限过宽。修复：icacls <key> /inheritance:r /grant:r "<本用户>:F" 移除继承并仅授本用户完全控制，随后 ssh 正常。来源：FSTDD009 接入 fstdd-hub 首连实测（Win11 专业版 22621）。