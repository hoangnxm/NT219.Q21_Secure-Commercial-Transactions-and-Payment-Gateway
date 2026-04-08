<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

// Endpoint mà Python port 5000 đang gọi
Route::post('/payments/cancel', function (Request $request) {
    error_log("-> Da nhan tin hieu huy don tu Python!");
    
    return response()->json([
        'status' => 'success',
        'message' => 'Laravel 11 da nhan lenh rollback'
    ], 200);
});