<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class AuditLog extends Model
{
    use HasFactory;

    // Khai báo các cột được phép insert data
    protected $fillable = [
        'event',
        'payload',
        'signature'
    ];
}
