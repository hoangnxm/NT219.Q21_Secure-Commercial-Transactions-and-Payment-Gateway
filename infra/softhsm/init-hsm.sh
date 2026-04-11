#!/bin/bash

# 1. Kiểm tra xem token đã được tạo chưa
if ! pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -L | grep -q "NT219_Token"; then
    echo "Token chưa tồn tại. Khởi tạo token mới..."
    softhsm2-util --init-token --slot 0 --label "NT219_Token" --so-pin 123456 --pin 1234
else
    echo "Token 'NT219_Token' đã tồn tại. Bỏ qua bước tạo Token."
fi

# 2. Kiểm tra khóa KÝ SỐ (RSA 2048)
if ! pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -l --pin 1234 -O | grep -q "my_sign_key"; then
    echo "Tạo cặp khóa RSA KÝ SỐ..."
    pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -l --pin 1234 --keypairgen --key-type rsa:2048 --id 01 --label "my_sign_key"
else
    echo "Khóa 'my_sign_key' đã tồn tại. Bỏ qua."
fi

# 3. Kiểm tra KHÓA BỌC (AES 256)
if ! pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -l --pin 1234 -O | grep -q "my_wrapping_key"; then
    echo "Tạo khóa AES KHÓA BỌC..."
    pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -l --pin 1234 --keygen --key-type aes:256 --id 02 --label "my_wrapping_key"
else
    echo "Khóa 'my_wrapping_key' đã tồn tại. Bỏ qua."
fi

echo "Đã xử lý xong HSM và các khóa!"