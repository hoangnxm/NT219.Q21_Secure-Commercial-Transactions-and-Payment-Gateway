#!/bin/bash

# Nếu chưa có thư mục vendor, mượn một container rác để cài Composer
if [ ! -d "vendor" ]; then
    echo "Không có vendor! Đang tải Composer..."
    docker run --rm \
        -v $(pwd):/var/www/html \
        -w /var/www/html \
        laravelsail/php85-composer:latest \
        composer install --ignore-platform-reqs
    echo "Đã tải xong vendor!"
fi

# 2. Khởi động toàn bộ hệ thống của mày
echo "Đang bật Docker..."
docker compose up -d --wait

# 3. Tự động chạy Migrate
echo "Đang chạy Migrate..."
docker compose exec laravel.test php artisan migrate --force

echo "Mọi thứ đã sẵn sàng"