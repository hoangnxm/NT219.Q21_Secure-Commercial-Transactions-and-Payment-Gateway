# Đã nâng cấp lên PHP 8.3 theo đúng yêu cầu của composer.json
FROM php:8.3-apache

# Cài đặt thư viện lõi, Nodejs (nếu có build Vite) và Postgres PDO
RUN apt-get update && apt-get install -y \
    libpq-dev \
    unzip \
    git \
    nodejs \
    npm \
    && docker-php-ext-install pdo pdo_pgsql

# Bật module rewrite cho Apache
RUN a2enmod rewrite

# Cài Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html
COPY . .

# Build vendor và tài nguyên frontend (nếu có)
RUN composer install --no-dev --optimize-autoloader
RUN npm install && npm run build || true

# Phân quyền ghi cho Laravel
RUN chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache

# Cấu hình lại thư mục gốc của Apache
ENV APACHE_DOCUMENT_ROOT /var/www/html/public
RUN sed -ri -e 's!/var/www/html!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/sites-available/*.conf
RUN sed -ri -e 's!/var/www/!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

EXPOSE 80