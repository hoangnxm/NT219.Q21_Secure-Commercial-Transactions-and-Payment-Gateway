<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Stripe\Stripe;
use Stripe\PaymentIntent;

class PaymentController extends Controller
{
    public function charge(Request $request)
    {
        Stripe::setApiKey(env('STRIPE_SECRET'));

        // Lúc này Frontend nó chỉ gửi 2 món này sang thôi
        $amount = $request->input('amount', 50000); 
        $orderId = $request->input('order_id');

        try {
            // Chỉ KHỞI TẠO giao dịch, CHƯA confirm (xác nhận)
            $paymentIntent = PaymentIntent::create([
                'amount' => $amount,
                'currency' => 'vnd',
                // Nhét order_id vào để đối soát sau này
                'metadata' => [
                    'order_id' => $orderId,
                ],
                // Tính năng tự động hỗ trợ 3-D Secure cho Payment Element
                'automatic_payment_methods' => [
                    'enabled' => true,
                ],
            ]);

            // Trả cái chìa khóa (client_secret) về cho thằng Nguyễn Hoàng vẽ UI
            return response()->json([
                'client_secret' => $paymentIntent->client_secret,
                'order_id' => $orderId
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }
}
