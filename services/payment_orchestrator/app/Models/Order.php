<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Order extends Model
{
    protected $fillable = ['order_id', 'email', 'amount', 'fraud_score', 'fraud_action', 'status', 'stripe_payment_id', 'jws_signature'];
}
