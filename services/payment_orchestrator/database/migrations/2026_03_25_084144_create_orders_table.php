<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
{
    Schema::create('orders', function ($table) {
        $table->id();
        $table->string('order_id')->unique(); // Mã đơn
        $table->decimal('amount', 15, 2); 
        $table->integer('fraud_score')->nullable(); // Điểm AI chấm
        $table->string('fraud_action')->nullable(); // block/allow/3ds
        $table->string('stripe_payment_id')->nullable(); 
        $table->enum('status', ['PENDING', 'SUCCESS', 'FAILED', 'FRAUD_BLOCKED'])->default('PENDING');
        $table->text('jws_signature')->nullable(); // Lưu chữ ký SoftHSM
        $table->timestamps();
    });
}

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('orders');
    }
};
