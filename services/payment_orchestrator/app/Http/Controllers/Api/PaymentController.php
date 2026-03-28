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
                'automatic_payment_methods' =>[
                    'enabled' => true,
                ],
                'payment_method_options' => [
                    'card' => [
                        // Kích hoạt 3DS phụ thuộc theo lệnh AI
                        'request_three_d_secure' => $force3ds ? 'any' : 'automatic',
                    ],
                ],
            ]);

            // Ký số
            $jwsSignature = 'HSM_OFFLINE_TEMP';
            try{
                $stripeId = $paymentIntent->id;
                $orderInfo = "Order:{$orderId}|Amount:{$amount}|StripeID:{$stripeId}";

                $dataToSend = ['payload' => $orderInfo];

                $finalJson = json_encode($dataToSend, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

                // Tạo header bảo mật
                $timestamp = time();
                $nonce = bin2hex(random_bytes(16));
                $dataToHash = $timestamp . '.' . $nonce . '.' . $finalJson;

                // Mật khẩu HMAC
                $secret = env('HMAC_SECRET','chuoi_bi_mat_cua_nhom_NT219');
                $signature = hash_hmac('sha256',$dataToHash,$secret);

                // Gọi SoftHSM qua port 8443 (mTLS)
                $signRes = Http::withOptions([
                    'verify' => false,
                    'cert' => storage_path('certs/client.crt'),
                    'ssl_key' => storage_path('certs/client.key')
                ])->withHeaders([
                    'X-Signature' => $signature,
                    'X-Timestamp' => $timestamp,
                    'X-Nonce' => $nonce,
                ])->withBody($finalJson,'application/json')
                ->post('https://host.docker.internal:8443/api/sign');

                if($signRes->successful()){
                    $jwsSignature = $signRes->json('signature');
                } else{
                    $jwsSignature = 'SIGNING FAILED';
                    Log::error("SoftHSM Error: " . $signRes->body());
                }
            }catch(\Exception $hsmError){
                Log::error("HSM Connection Error: " . $hsmError->getMessage());
                $jwsSignature = 'HSM_OFFLINE_TEMP';
            }

            $order->update([
                'stripe_payment_id' => $paymentIntent->id,
                'jws_signature' => $jwsSignature,
                'status' => 'PENDING'
            ]);

            // Trả kết quả về FE
            return response()->json([
                'status' => 'success',
                'order_id' => $order->order_id,
                'amount' => $order->amount,
                'client_secret' => $paymentIntent->client_secret,
                'fraud_score' => $fraudData['score'],
                'action' => $fraudData['action'],
                'receipt_signature' => $jwsSignature,
                'jws_receipt' => $jwsSignature
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
        }
            // Trả về 200 OK. Nếu không, Stripe sẽ tưởng server sập và nó sẽ spam gọi lại liên tục.
            return response()->json(['status' => 'success'], 200);
    }

}
