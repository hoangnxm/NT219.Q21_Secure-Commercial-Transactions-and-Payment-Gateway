<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Api\PaymentController;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

<<<<<<< HEAD
Route::post('/payments/charge', [PaymentController::class, 'charge']);
=======
Route::post('/payments/charge', [PaymentController::class, 'charge']);

Route::post('/webhook/stripe', [\App\Http\Controllers\Api\PaymentController::class, 'handleWebhook']);
>>>>>>> feat/stripe-checkout-and-order-service
