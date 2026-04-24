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
use Carbon\Carbon;

class PaymentController extends Controller
{
    public function charge(Request $request)
    {
        Stripe::setApiKey(env('STRIPE_SECRET'));

       // Nhận dữ liệu từ backend
        $amount = $request->input('amount'); 
        $orderId = $request->input('order_id');
        $email = trim($request->input('email'));

        // LOG ĐỂ SOI DỮ LIỆU
        Log::info("--- TEST GIAO DICH ---");
        Log::info("Email nhan duoc: '" . $email . "'");

        // Phân tích device
        $userAgent = $request->header('User-Agent');
        $device = str_contains(strtolower($userAgent),'mobile')? "Mobile" : "Desktop";

        // Đếm số lần failed trong DB thay vì request trong 30P trước
        $failedAttempts = Order::where('email',$email)
                                ->where('status','FAILED')
                                ->where('created_at', '>=', Carbon::now()->subMinutes(30))
                                ->count();

        // Đóng gói đem đi chấm điểm
        $fraudPayload = [
            'amount' => (float) $amount,
            'email' => $email,
            'ip_address' => $request->ip()??"127.0.0.1",
            'device' => $device,
            'failed_attempts' => $failedAttempts,
            'hour_of_day' => Carbon::now()->hour
        ];

        try {
           $fraudRes = Http::timeout(5)->post('http://fraud-engine-service.nt219-project.svc.cluster.local:8001/api/fraud/score', $fraudPayload);

            // Nếu Python lỗi và không trả data
            if (!$fraudRes->successful()) {
            return response()->json([
                'error' => 'AI bị lỗi ',
                'detail' => $fraudRes->json() // In lỗi
            ], 500);
            }

            $fraudData = $fraudRes->json();

            Log::info("AI Decision: " . $fraudData['action'] . " (Score: " . $fraudData['score'] . ")");

            $order = Order::create([
                'order_id' => $orderId,
                'email' => $email,
                'amount' => $amount,
                'fraud_score' => $fraudData['score'],
                'fraud_action' => $fraudData['action'],
                'status' => ($fraudData['action'] === 'block') ? 'FRAUD_BLOCKED' : 'PENDING'
            ]);

            // Xử lí theo quyết định AI
            if($fraudData['action'] === 'block'){
                $this->logSecurityEvent('FRAUD_BLOCK_ACTION', [
                    'order_id' => $orderId,
                    'email' => $email,
                    'fraud_score' => $fraudData['score'],
                    'reason' => $fraudData['reason'],
                    'ip' => $request->ip()
                ]);


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
            'receipt_email' => $email, // Gắn email vào hóa đơn Stripe
            'metadata' => [
            'order_id' => $orderId,
            'fraud_score' => $fraudData['score']
        ],
        // Cấu hình 3DS dựa trên Fraud Engine
        'payment_method_options' => [
            'card' => [
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
                ->post('https://softhsm.nt219-project.svc.cluster.local:8888/api/sign');

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
        'client_secret' => $paymentIntent->client_secret, // Bắt buộc phải có để trả về FE
        'fraud_score' => $fraudData['score'],
        'action' => $fraudData['action'],
        'receipt_signature' => $jwsSignature,
        'jws_receipt' => $jwsSignature
    ]);

        } catch (\Exception $e) {
            Log::error("FRAUD ENGINE CONNECTION ERROR: " . $e->getMessage());

            return response()->json([
                'error' => 'Không thể kết nối với hệ thống AI Fraud Engine!',
                'detail' => $e->getMessage(),
                'suggestion' => 'Kiểm tra xem container Fraud Engine đã bật chưa hoặc sai URL http://fraud_engine:8001'
            ], 500);
        }
    }

    public function handleWebhook(Request $request) 
    {
        $endpoint_secret = env('STRIPE_WEBHOOK_SECRET');

        // 1. Lấy raw payload và header chữ ký
        $payload = $request->getContent();
        $sig_header = $request->header('Stripe-Signature');
        $event = null;

        // 2. Xác minh chữ ký (Nhiệm vụ 3)
        try {
            $event = \Stripe\Webhook::constructEvent(
                $payload, $sig_header, $endpoint_secret
            );
        } catch(\UnexpectedValueException $e) {
            // Payload không hợp lệ
            Log::error('Webhook error: Invalid payload.');
            return response()->json(['error' => 'Invalid payload'], 400);
        } catch(\Stripe\Exception\SignatureVerificationException $e) {
            // Chữ ký không hợp lệ (Hacker giả mạo)
            Log::error('Webhook error: Invalid signature.');
            return response()->json(['error' => 'Invalid signature'], 400);
        }

        // 3. Xử lý các Event (Nhiệm vụ 4)
        switch ($event->type) {
            case 'payment_intent.succeeded':
                $paymentIntent = $event->data->object;
                $order = Order::where('stripe_payment_id', $paymentIntent->id)->first();
                
                if($order){
                    $order->update(['status' => 'SUCCESS']);

                    $this->logSecurityEvent('PAYMENT_SUCCESS_FINAL', [
                        'order_id' => $order->order_id,
                        'stripe_id' => $paymentIntent->id,
                        'amount' => $paymentIntent->amount / 100,
                        'currency' => $paymentIntent->currency
                    ]);

                    Log::info("Webhook: Đơn {$order->order_id} thanh toán thành công.");
                }
                break;

            case 'payment_intent.payment_failed':
                $paymentIntent = $event->data->object;
                $order = Order::where('stripe_payment_id', $paymentIntent->id)->first();
                
                if($order){
                    $order->update(['status' => 'FAILED']);

                    $this->logSecurityEvent('PAYMENT_FAILED_ALERT', [
                        'order_id' => $order->order_id,
                        'stripe_id' => $paymentIntent->id,
                        'error_message' => $paymentIntent->last_payment_error ? $paymentIntent->last_payment_error->message : 'Unknown error'
                    ]);

                    Log::warning("Webhook: Đơn {$order->order_id} thanh toán thất bại.");
                }
                break;

            default:
                Log::info("Webhook: Nhận được event không xử lý ({$event->type}).");
        }

        // Luôn trả về 200 để Stripe biết server đã nhận thành công
        return response()->json(['status' => 'success'], 200);
    }

    # API Cung cấp trạng thái để fastAPI đối soát
    public function getStatus($order_id){
        $order = Order::where('order_id',$order_id)->first();

        if(!$order){
            return response()->json([
                'error' => 'Không tìm thấy đơn hàng trên Cổng thanh toán'
            ], 404);
        }

        return response()->json([
            'order_id' => $order->order_id,
            'amount' => $order->amount,
            'status' => $order->status
        ]);
    }

    // API Huỷ đơn khi gặp lỗi
    public function cancelOrder(Request $request)
    {
        $order = Order::where('order_id', $request->order_id)->first();
        if ($order && $order->status === 'PENDING') {
            $order->status = 'FAILED'; // Chuyển trạng thái thành FAILED
            $order->save();
            return response()->json(['message' => 'Đã hủy đơn hàng thành công']);
        }
        return response()->json(['error' => 'Không tìm thấy đơn hợp lệ để hủy'], 400);
    }

    private function logSecurityEvent($event, $data){
        $payload = json_encode($data);
        $timestamp = time();
        $nonce = bin2hex(random_bytes(16));

        // Gửi sang Softhsm để ký niêm phong bảng log
        try{
            $response = Http::withOptions(['verify' => false])
                ->withHeaders([
                    'X-Signature' => hash_hmac('sha256', $timestamp . $payload, env('HMAC_SECRET')),
                    'X-Timestamp' => $timestamp,
                    'X-Nonce' => $nonce
                ])
                ->post('https://softhsm.nt219-project.svc.cluster.local:8888/api/sign', ['payload' => $payload]);

            if($response->successful()){
                \App\Models\AuditLog::create([
                    'event' => $event,
                    'payload' => $payload,
                    'signature' => $response->json('signature') // Lưu chữ kí vào DB
                ]);
            }
        }catch(\Exception $e){
            Log::error("Không thể ghi Audit Log bảo mật: " . $e->getMessage());
        }
    }
}
