<?php

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // Dán đoạn code bỏ qua CSRF vào đây:
        $middleware->validateCsrfTokens(except: [
            'api/webhook', // Đảm bảo URL này khớp với route bạn định nghĩa
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        //
    })->create();