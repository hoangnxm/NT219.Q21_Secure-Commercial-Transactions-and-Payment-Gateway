#!/bin/bash
# 1. Khởi tạo Slot 0
softhsm2-util --init-token --slot 0 --label "NT219_Token" --so-pin 123456 --pin 1234

# 2. Tạo cặp khóa RSA 2048-bit để KÝ SỐ (Signing Key)
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -l --pin 1234 --keypairgen --key-type rsa:2048 --id 01 --label "my_sign_key"

# 3. Tạo khóa AES-256 để làm KHÓA BỌC (Wrapping Key) -> ĐÚNG CHUẨN REQUIREMENT
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -l --pin 1234 --keygen --key-type aes:256 --id 02 --label "my_wrapping_key"

echo "Đã tạo HSM và cặp khóa RSA thành công!"