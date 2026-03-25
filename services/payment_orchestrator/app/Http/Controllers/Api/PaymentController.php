<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Order;
use Illuminate\Http\Request;
use Stripe\Stripe;
use Stripe\PaymentIntent;
use Illuminate\Support\Facades\Http;
use Nette\Utils\Json;
use Illuminate\Support\Facades\Log;

class PaymentController extends Controller
{
    public function charge(Request $request)
    {
        Stripe::setApiKey(env('STRIPE_SECRET'));

        // Lúc này Frontend nó chỉ gửi 2 món này sang thôi
        $amount = $request->input('amount', 50000); 
        $orderId = $request->input('order_id');

        // Query số lần thất bại, giờ mock tạm là 0 hoặc 1 để test
        $failedAttempts = $request->input('failed_attempts', 0);

        try {
            // Gọi Fraud Engine xin điểm rủi ro
            $fraudRes = Http::timeout(5)->post('http://host.docker.internal:8001/api/fraud/score',[
                'amount' => $amount,
                'failed_attempts' => $failedAttempts
            ]);

            // Nếu Python lỗi và không trả data
            if (!$fraudRes->successful()) {
            return response()->json([
                'error' => 'AI bị lỗi ',
                'detail' => $fraudRes->json() // In lỗi
            ], 500);
            }

            $fraudData = $fraudRes->json();

            $order = Order::create([
                'order_id' => $orderId,
                'amount' => $amount,
                'fraud_score' => $fraudData['score'],
                'fraud_action' => $fraudData['action'],
                'status' => ($fraudData['action'] === 'block') ? 'FRAUD_BLOCKED' : 'PENDING'
            ]);

            // Xử lí theo quyết định AI
            if($fraudData['action'] === 'block'){
                return response()->json([
                    'error' => "Giao dịch bị từ chối do rủi ro gian lận cao",
                    'fraud_score' => $fraudData['score'],
                    'reason' => $fraudData['reason']
                ], 403);
            }

            // Nếu AI khả nghi thì bật force3ds true
            $force3ds = ($fraudData['action'] === 'force_3ds');

            // Chuyển tiếp cho Stripe(PSP)
            Stripe::setApiKey(env('STRIPE_SECRET'));
            $paymentIntent = PaymentIntent::create([
                'amount' => $amount,
                'currency' => 'vnd',
                'metadata' => [
                    'order_id' => $orderId,
                    'fraud_score' => $fraudData['score']
                ],
                'payment_method_options' => [
                    'card' => [
                        // Kích hoạt 3DS phụ thuộc theo lệnh AI
                        'request_three_d_secure' => $force3ds ? 'any' : 'automatic',
                    ],
                ],
            ]);

            // Chuẩn bị data để ky số 
            $dataToSignArray = [
                'payload' => "Order:{$order->order_id}|Amount:{$amount}|StripeID:{$paymentIntent->id}"
            ];
            $bodyJson = json_encode($dataToSignArray);

            // Lấy Secret_Key
            $secret = env('HMAC_SECRET');

            // Băm HMAC-SHA256 để tạo chữ ký xác thực nội bộ
            $signature = hash_hmac('sha256',$bodyJson,$secret);

            $signRes = Http::withHeaders([
                'X-Signature' => $signature,
                'Content-Type' => 'application/json'
            ])->withBody($bodyJson,'application/json')
            ->post('http://host.docker.internal:8888/api/sign');

            // Lấy chuỗi Base64 từ trường 'signature' lưu vào cột jws_signature
            $jwsSignature = $signRes->successful() ? $signRes->json('signature') : 'SIGNING_FAILED';

            $order->update([
                'stripe_payment_id' => $paymentIntent->id,
                'jws_signature' => $jwsSignature,
                'status' => 'PENDING'
            ]);

            // Trả kết quả về FE
            return response()->json([
                'client_secret' => $paymentIntent->client_secret,
                'fraud_score' => $fraudData['score'],
                'action' => $fraudData['action'],
                'receipt_signature' => $jwsSignature
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    public function handleWebhook(Request $request){
        $payload = $request->all();

        // Kiểm tra xem có phải thanh toán thành công không
        if(isset($payload['type']) &&  $payload['type'] === 'payment_intent.succeeded'){
            $paymentIntent = $payload['data']['object'];
            $stripeId = $paymentIntent['id'];

            $order = Order::where('stripe_payment_id',$stripeId)->first();

            if($order){
                $order->update(['status' => 'SUCCESS']);

                Log::info("Khách đã nhập OTP. Đơn {$order->order_id} thanh toán thành công");
            }
            // Trả về 200 OK. Nếu không, Stripe sẽ tưởng server sập và nó sẽ spam gọi lại liên tục.
            return response()->json(['status' => 'success'], 200);
        }
    }
}
