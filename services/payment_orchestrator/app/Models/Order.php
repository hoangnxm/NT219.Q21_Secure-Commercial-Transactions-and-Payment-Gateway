<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Order extends Model
{
    protected $fillable = ['order_id', 'amount', 'fraud_score', 'fraud_action', 'status', 'jws_signature'];
}
