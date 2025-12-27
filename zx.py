#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 بوت متجر الحسابات والمنتجات الرقمية - النسخة النهائية المتكاملة
👑 المطور: Ayuob
📧 التواصل: @AyuobZaalani
📢 القناة: @marketing_algeri
🔗 رابط النقاط: https://t.me/marketing_algeri/3?single
"""

import asyncio
import sqlite3
import json
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import secrets

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ==================== ⚙️ إعدادات البوت ====================
BOT_TOKEN = "8544540684:AAEw_t8RQhYLa_afGfHXcEcVZ4TDuHDU3ZA"
ADMIN_ID = 7130722086  # المالك الأساسي
ADMIN_CONTACT = "@AyuobZaalani"  # التواصل للبيع
REQUIRED_CHANNEL = "@marketing_algeri"  # القناة الإجبارية
CHANNEL_POINTS_LINK = "https://t.me/marketing_algeri/3?single"  # رابط النقاط
REFERRAL_POINTS = 3  # نقاط كل إحالة

# إعدادات الدفع
CURRENCY_NAME = "نقطة"
CURRENCY_SYMBOL = "⭐"

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالات المحادثة
ADD_PRODUCT_NAME, ADD_PRODUCT_DESC, ADD_PRODUCT_PRICE, ADD_PRODUCT_STOCK, ADD_PRODUCT_CATEGORY, ADD_PRODUCT_TYPE = range(6)
EDIT_PRODUCT_CHOICE = 10
ADD_AD_TITLE, ADD_AD_DESC, ADD_AD_PRICE, ADD_AD_IMAGES, ADD_AD_CONFIRM = range(11, 16)
ADD_POINTS_LINK_POINTS, ADD_POINTS_LINK_USERS, ADD_POINTS_LINK_HOURS = range(16, 19)
TRANSFER_POINTS_USER, TRANSFER_POINTS_AMOUNT = range(19, 21)
BROADCAST_MESSAGE = 21
ADD_POINTS_TO_USER, ADD_POINTS_AMOUNT = range(22, 24)
SEARCH_QUERY = 24
CREATE_POINT_LINK_CONFIRM = 25

# ==================== 🏗️ قاعدة البيانات المتكاملة ====================
class CompleteDatabase:
    def __init__(self, db_name="complete_shop.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        """إنشاء جميع جداول قاعدة البيانات"""
        cursor = self.conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                points INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                referrals_earned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                last_active TIMESTAMP,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unlimited_points INTEGER DEFAULT 0
            )
        ''')
        
        # جدول الفئات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                icon TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        
        # جدول المنتجات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name TEXT,
                description TEXT,
                price INTEGER,
                stock INTEGER DEFAULT -1,
                sold_count INTEGER DEFAULT 0,
                product_type TEXT DEFAULT 'account',
                delivery_type TEXT DEFAULT 'auto',
                requires_admin INTEGER DEFAULT 0,
                is_featured INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        # جدول الطلبات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT UNIQUE,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                total_points INTEGER,
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                delivery_data TEXT,
                requires_admin_action INTEGER DEFAULT 0,
                admin_assigned INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # جدول طلبات النقاط
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS point_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                proof_text TEXT,
                proof_image TEXT,
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول الإحالات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                points_awarded INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول الإشعارات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تحويل النقاط بين المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS point_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                to_user_id INTEGER,
                amount INTEGER,
                status TEXT DEFAULT 'completed',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users(user_id),
                FOREIGN KEY (to_user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول روابط النقاط المؤقتة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS point_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_code TEXT UNIQUE,
                created_by INTEGER,
                points_per_user REAL,
                max_users INTEGER,
                used_count INTEGER DEFAULT 0,
                expiry_time TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        ''')
        
        # جدول إعلانات المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                price REAL,
                images TEXT,
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                admin_price_adjustment REAL DEFAULT 0,
                final_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ تم إنشاء قاعدة البيانات المتكاملة")
        
        # إضافة البيانات الأولية
        self.add_initial_data()
    
    def add_initial_data(self):
        """إضافة البيانات الأولية"""
        cursor = self.conn.cursor()
        
        # إضافة الأدمن مع نقاط غير محدودة
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, points, is_admin, unlimited_points)
                VALUES (?, ?, ?, ?, 1, 1)
            ''', (ADMIN_ID, "Ayuob", "Ayuob", 1000000))
        except sqlite3.OperationalError as e:
            logger.error(f"خطأ في إضافة الأدمن: {e}")
            cursor.execute('ALTER TABLE users ADD COLUMN unlimited_points INTEGER DEFAULT 0')
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, points, is_admin, unlimited_points)
                VALUES (?, ?, ?, ?, 1, 1)
            ''', (ADMIN_ID, "Ayuob", "Ayuob", 1000000))
        
        # إضافة الفئات
        categories = [
            ("👤 حسابات مميزة", "👤", "حسابات خدمات البث والموسيقى", 1),
            ("🎮 ألعاب وشحنات", "🎮", "حسابات ألعاب وشراء شحنات", 2),
            ("📱 تطبيقات وبرامج", "📱", "تطبيقات مفعلة وبرامج مكركة", 3),
            ("🔧 أدوت وتسريعات", "🔧", "أدوات رقمية وتسريعات", 4),
            ("🎬 محتوى رقمي", "🎬", "محتوى مرئي وسمعي", 5),
            ("📊 خدمات تسويقية", "📊", "خدمات تسويق وسوشيال ميديا", 6),
            ("📢 إعلانات المستخدمين", "📢", "منتجات يبيعها المستخدمون", 7)
        ]
        
        for name, icon, desc, order in categories:
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, icon, description, sort_order)
                VALUES (?, ?, ?, ?)
            ''', (name, icon, desc, order))
        
        # إضافة منتجات افتراضية
        sample_products = [
            (1, "حساب نتفليكس بريميوم", "حساب نتفليكس بريميوم لمدة شهر", 150, 50, 0, 1),
            (1, "حساب سبوتيفاي بريميوم", "سبوتيفاي بريميوم بدون إعلانات", 100, 100, 0, 1),
            (2, "حساب ستيم مع ألعاب", "حساب ستيم مع 5 ألعاب مشهورة", 300, 25, 1, 1),
            (3, "تطبيق يوتيوب بريميوم", "يوتيوب بريميوم بدون إعلانات", 80, -1, 0, 0),
            (6, "خدمة زيادة متابعين", "زيادة 1000 متابع إنستغرام", 200, -1, 1, 1)
        ]
        
        for cat_id, name, desc, price, stock, requires_admin, featured in sample_products:
            cursor.execute('''
                INSERT OR IGNORE INTO products 
                (category_id, name, description, price, stock, requires_admin, is_featured, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (cat_id, name, desc, price, stock, requires_admin, featured))
        
        self.conn.commit()
        logger.info("✅ تمت إضافة البيانات الأولية")
    
    # ==================== 👥 دوال المستخدمين ====================
    def register_user(self, user_id: int, username: str, first_name: str, referred_by: int = None):
        """تسجيل مستخدم جديد"""
        cursor = self.conn.cursor()
        referral_code = f"REF{user_id}{random.randint(1000, 9999)}"
        
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, referral_code, referred_by, last_active)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, referral_code, referred_by))
        
        # إذا كان هناك محيل، منح النقاط
        if referred_by:
            cursor.execute('UPDATE users SET points = points + ?, referrals_count = referrals_count + 1, referrals_earned = referrals_earned + ? WHERE user_id = ?', 
                          (REFERRAL_POINTS, REFERRAL_POINTS, referred_by))
            
            cursor.execute('INSERT INTO referrals (referrer_id, referred_id, points_awarded) VALUES (?, ?, ?)', 
                          (referred_by, user_id, REFERRAL_POINTS))
            
            cursor.execute('UPDATE users SET points = points + ? WHERE user_id = ?', 
                          (REFERRAL_POINTS, user_id))
            
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message)
                VALUES (?, ?, ?)
            ''', (referred_by, "🎉 إحالة جديدة!", 
                  f"لقد قام {first_name} بالتسجيل عبر رابطك وحصلت على {REFERRAL_POINTS} {CURRENCY_SYMBOL}"))
        
        self.conn.commit()
        return referral_code
    
    def get_user(self, user_id: int):
        """الحصول على بيانات المستخدم"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def update_user_points(self, user_id: int, points: int, operation: str = "add"):
        """تحديث نقاط المستخدم"""
        cursor = self.conn.cursor()
        user = self.get_user(user_id)
        
        if not user:
            return False
        
        if operation == "subtract" and user.get('unlimited_points') == 1:
            cursor.execute('UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?', 
                          (points, user_id))
        else:
            if operation == "add":
                cursor.execute('UPDATE users SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?', 
                              (points, points, user_id))
            elif operation == "subtract":
                cursor.execute('UPDATE users SET points = points - ?, total_spent = total_spent + ? WHERE user_id = ?', 
                              (points, points, user_id))
        
        self.conn.commit()
        return True
    
    def is_admin(self, user_id: int):
        """التحقق إذا كان المستخدم أدمن"""
        user = self.get_user(user_id)
        return user and user['is_admin'] == 1
    
    def update_last_active(self, user_id: int):
        """تحديث آخر نشاط للمستخدم"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_user_stats(self, user_id: int):
        """الحصول على إحصائيات المستخدم"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        user = self.get_user(user_id)
        if user:
            stats.update(user)
        
        cursor.execute('SELECT COUNT(*) FROM orders WHERE user_id = ?', (user_id,))
        stats['total_orders'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = "completed"', (user_id,))
        stats['completed_orders'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_points) FROM orders WHERE user_id = ? AND status = "completed"', (user_id,))
        stats['total_purchases'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND points_awarded > 0', (user_id,))
        stats['active_referrals'] = cursor.fetchone()[0]
        
        return stats
    
    # ==================== 💰 دوال تحويل النقاط ====================
    def transfer_points(self, from_user_id: int, to_user_id: int, amount: int):
        """تحويل نقاط من مستخدم لآخر"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT points, unlimited_points FROM users WHERE user_id = ?', (from_user_id,))
        sender = cursor.fetchone()
        
        if not sender:
            return False, "المرسل غير موجود"
        
        sender_points, unlimited_points = sender
        
        if unlimited_points != 1 and sender_points < amount:
            return False, f"رصيدك غير كافي ({sender_points}/{amount})"
        
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (to_user_id,))
        if not cursor.fetchone():
            return False, "المستقبل غير موجود"
        
        if unlimited_points != 1:
            cursor.execute('UPDATE users SET points = points - ?, total_spent = total_spent + ? WHERE user_id = ?',
                          (amount, amount, from_user_id))
        
        cursor.execute('UPDATE users SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?',
                      (amount, amount, to_user_id))
        
        cursor.execute('''
            INSERT INTO point_transfers (from_user_id, to_user_id, amount, status)
            VALUES (?, ?, ?, 'completed')
        ''', (from_user_id, to_user_id, amount))
        
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message)
            VALUES (?, ?, ?)
        ''', (from_user_id, "📤 تحويل نقاط", 
              f"تم تحويل {amount} {CURRENCY_SYMBOL} إلى المستخدم #{to_user_id}"))
        
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message)
            VALUES (?, ?, ?)
        ''', (to_user_id, "📥 استلام نقاط", 
              f"استلمت {amount} {CURRENCY_SYMBOL} من المستخدم #{from_user_id}"))
        
        self.conn.commit()
        return True, "تم التحويل بنجاح"
    
    # ==================== 🔗 دوال روابط النقاط المؤقتة ====================
    def create_point_link(self, created_by: int, points_per_user: float, max_users: int, hours_valid: int):
        """إنشاء رابط نقاط مؤقت"""
        cursor = self.conn.cursor()
        
        link_code = secrets.token_urlsafe(12)
        expiry_time = datetime.now() + timedelta(hours=hours_valid)
        
        cursor.execute('''
            INSERT INTO point_links (link_code, created_by, points_per_user, max_users, expiry_time, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (link_code, created_by, points_per_user, max_users, expiry_time))
        
        link_id = cursor.lastrowid
        self.conn.commit()
        
        return link_id, link_code
    
    def get_point_link(self, link_code: str):
        """الحصول على رابط نقاط"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM point_links WHERE link_code = ? AND is_active = 1', (link_code,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def use_point_link(self, link_code: str, user_id: int):
        """استخدام رابط نقاط"""
        cursor = self.conn.cursor()
        
        link = self.get_point_link(link_code)
        if not link:
            return False, "الرابط غير صالح أو منتهي"
        
        expiry_time = datetime.strptime(link['expiry_time'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiry_time:
            cursor.execute('UPDATE point_links SET is_active = 0 WHERE id = ?', (link['id'],))
            self.conn.commit()
            return False, "انتهت صلاحية الرابط"
        
        if link['used_count'] >= link['max_users']:
            cursor.execute('UPDATE point_links SET is_active = 0 WHERE id = ?', (link['id'],))
            self.conn.commit()
            return False, "وصل الرابط للحد الأقصى من المستخدمين"
        
        cursor.execute('''
            SELECT COUNT(*) FROM point_transfers 
            WHERE notes LIKE ? AND to_user_id = ?
        ''', (f"%LINK:{link_code}%", user_id))
        
        if cursor.fetchone()[0] > 0:
            return False, "لقد استخدمت هذا الرابط من قبل"
        
        points = int(link['points_per_user'])
        self.update_user_points(user_id, points, "add")
        
        cursor.execute('UPDATE point_links SET used_count = used_count + 1 WHERE id = ?', (link['id'],))
        
        cursor.execute('''
            INSERT INTO point_transfers (from_user_id, to_user_id, amount, status, notes)
            VALUES (?, ?, ?, 'completed', ?)
        ''', (link['created_by'], user_id, points, f"من رابط نقاط: {link_code}"))
        
        if link['used_count'] + 1 >= link['max_users']:
            cursor.execute('UPDATE point_links SET is_active = 0 WHERE id = ?', (link['id'],))
        
        self.conn.commit()
        return True, f"تم إضافة {points} {CURRENCY_SYMBOL} إلى رصيدك"
    
    def get_active_point_links(self, created_by: int = None):
        """الحصول على روابط النقاط النشطة"""
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM point_links WHERE is_active = 1'
        params = []
        
        if created_by:
            query += ' AND created_by = ?'
            params.append(created_by)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    # ==================== 📢 دوال إعلانات المستخدمين ====================
    def create_user_ad(self, user_id: int, title: str, description: str, price: float, images_json: str):
        """إنشاء إعلان جديد"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_ads (user_id, title, description, price, images, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (user_id, title, description, price, images_json))
        
        ad_id = cursor.lastrowid
        self.conn.commit()
        return ad_id
    
    def get_user_ads(self, user_id: int = None, status: str = None):
        """الحصول على إعلانات المستخدمين"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT a.*, u.username, u.first_name 
            FROM user_ads a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE 1=1
        '''
        params = []
        
        if user_id:
            query += ' AND a.user_id = ?'
            params.append(user_id)
        
        if status:
            query += ' AND a.status = ?'
            params.append(status)
        
        query += ' ORDER BY a.created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_pending_ads(self):
        """الحصول على الإعلانات المعلقة"""
        return self.get_user_ads(status='pending')
    
    def get_ad(self, ad_id: int):
        """الحصول على إعلان محدد"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT a.*, u.username, u.first_name 
            FROM user_ads a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.id = ?
        ''', (ad_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def update_ad_status(self, ad_id: int, status: str, admin_notes: str = None, 
                        price_adjustment: float = 0, final_price: float = None):
        """تحديث حالة الإعلان"""
        cursor = self.conn.cursor()
        
        updates = {
            'status': status,
            'admin_notes': admin_notes,
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if price_adjustment != 0:
            updates['admin_price_adjustment'] = price_adjustment
        
        if final_price is not None:
            updates['final_price'] = final_price
        
        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(ad_id)
        
        cursor.execute(f'UPDATE user_ads SET {set_clause} WHERE id = ?', values)
        
        ad = self.get_ad(ad_id)
        if ad:
            status_text = "✅ مقبول" if status == 'approved' else "❌ مرفوض" if status == 'rejected' else "⏳ معلق"
            message = f"📢 تم تحديث حالة إعلانك '{ad['title']}' إلى: {status_text}"
            
            if admin_notes:
                message += f"\n📝 ملاحظات الأدمن: {admin_notes}"
            
            if final_price and status == 'approved':
                message += f"\n💰 السعر النهائي: {final_price} {CURRENCY_SYMBOL}"
            
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message)
                VALUES (?, ?, ?)
            ''', (ad['user_id'], "📢 تحديث حالة الإعلان", message))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def approve_ad_to_product(self, ad_id: int, category_id: int):
        """تحويل إعلان معتمد إلى منتج في المتجر"""
        ad = self.get_ad(ad_id)
        if not ad or ad['status'] != 'approved':
            return False, "الإعلان غير معتمد"
        
        product_id = self.add_product(
            category_id=category_id,
            name=ad['title'],
            description=ad['description'],
            price=int(ad['final_price'] or ad['price']),
            stock=-1,
            requires_admin=1,
            is_featured=0,
            product_type="user_product",
            delivery_type="admin"
        )
        
        self.update_ad_status(ad_id, 'converted', f"تم تحويله إلى منتج #{product_id}")
        
        return True, f"تم تحويل الإعلان إلى منتج #{product_id}"
    
    # ==================== 📁 دوال الفئات ====================
    def get_categories(self):
        """الحصول على جميع الفئات"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.*, COUNT(p.id) as product_count 
            FROM categories c 
            LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1 
            WHERE c.is_active = 1 
            GROUP BY c.id 
            ORDER BY c.sort_order, c.name
        ''')
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_category(self, category_id: int):
        """الحصول على فئة محددة"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def add_category(self, name: str, icon: str = "", description: str = ""):
        """إضافة فئة جديدة"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO categories (name, icon, description, is_active, sort_order)
            VALUES (?, ?, ?, 1, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM categories))
        ''', (name, icon, description))
        
        category_id = cursor.lastrowid
        self.conn.commit()
        return category_id
    
    def delete_category(self, category_id: int):
        """حذف فئة"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE categories SET is_active = 0 WHERE id = ?', (category_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # ==================== 🛒 دوال المنتجات ====================
    def get_products(self, category_id: int = None, featured_only: bool = False, active_only: bool = True):
        """الحصول على المنتجات"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT p.*, c.name as category_name, c.icon as category_icon 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE 1=1
        '''
        params = []
        
        if active_only:
            query += ' AND p.is_active = 1'
        
        if featured_only:
            query += ' AND p.is_featured = 1'
        
        if category_id:
            query += ' AND p.category_id = ?'
            params.append(category_id)
        
        query += ' ORDER BY p.is_featured DESC, p.created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_product(self, product_id: int):
        """الحصول على منتج محدد"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.id = ?
        ''', (product_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def add_product(self, category_id: int, name: str, description: str, price: int, 
                   stock: int = -1, requires_admin: int = 0, is_featured: int = 0,
                   product_type: str = "account", delivery_type: str = "auto"):
        """إضافة منتج جديد"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO products 
            (category_id, name, description, price, stock, product_type, 
             delivery_type, requires_admin, is_featured, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (category_id, name, description, price, stock, product_type, 
              delivery_type, requires_admin, is_featured))
        
        product_id = cursor.lastrowid
        self.conn.commit()
        return product_id
    
    def update_product(self, product_id: int, **kwargs):
        """تحديث بيانات المنتج"""
        if not kwargs:
            return False
        
        cursor = self.conn.cursor()
        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(product_id)
        
        cursor.execute(f'UPDATE products SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_product(self, product_id: int):
        """حذف منتج"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE products SET is_active = 0 WHERE id = ?', (product_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_product_stock(self, product_id: int, quantity: int):
        """تحديث مخزون المنتج"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET stock = stock - ?, sold_count = sold_count + ? 
            WHERE id = ? AND (stock = -1 OR stock >= ?)
        ''', (quantity, quantity, product_id, quantity))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # ==================== 📦 دوال الطلبات ====================
    def create_order(self, user_id: int, product_id: int, quantity: int = 1):
        """إنشاء طلب جديد"""
        cursor = self.conn.cursor()
        
        product = self.get_product(product_id)
        if not product:
            return None, None, None
        
        if product['stock'] != -1 and product['stock'] < quantity:
            return None, None, None
        
        total_points = product['price'] * quantity
        
        user = self.get_user(user_id)
        if not user:
            return None, None, None
        
        if user.get('unlimited_points') != 1 and user['points'] < total_points:
            return None, None, None
        
        order_code = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
        
        cursor.execute('''
            INSERT INTO orders 
            (order_code, user_id, product_id, quantity, total_points, requires_admin_action)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_code, user_id, product_id, quantity, total_points, product['requires_admin']))
        
        order_id = cursor.lastrowid
        self.conn.commit()
        return order_id, order_code, total_points
    
    def complete_order(self, order_id: int, delivery_data: str = None, admin_notes: str = None):
        """إكمال الطلب"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE orders 
            SET status = 'completed', delivery_data = ?, admin_notes = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (delivery_data, admin_notes, order_id))
        self.conn.commit()
    
    def cancel_order(self, order_id: int, reason: str = None):
        """إلغاء الطلب"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT user_id, total_points FROM orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        
        if order:
            user_id, total_points = order
            user = self.get_user(user_id)
            if not user or user.get('unlimited_points') != 1:
                self.update_user_points(user_id, total_points, "add")
        
        cursor.execute('''
            UPDATE orders 
            SET status = 'cancelled', admin_notes = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (reason, order_id))
        self.conn.commit()
    
    def get_order_by_id(self, order_id: int):
        """الحصول على طلب بواسطة ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, p.name as product_name, u.username as customer_name, u.first_name
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            JOIN users u ON o.user_id = u.user_id 
            WHERE o.id = ?
        ''', (order_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_order(self, order_code: str):
        """الحصول على طلب محدد"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, p.name as product_name, u.username as customer_name, u.first_name
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            JOIN users u ON o.user_id = u.user_id 
            WHERE o.order_code = ?
        ''', (order_code,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_user_orders(self, user_id: int, limit: int = 20):
        """الحصول على طلبات المستخدم"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, p.name as product_name 
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.user_id = ? 
            ORDER BY o.created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_pending_orders(self, requires_admin: bool = None):
        """الحصول على الطلبات المعلقة"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT o.*, p.name as product_name, u.username as customer_name, u.first_name
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            JOIN users u ON o.user_id = u.user_id 
            WHERE o.status = 'pending'
        '''
        
        params = []
        if requires_admin is not None:
            query += ' AND o.requires_admin_action = ?'
            params.append(1 if requires_admin else 0)
        
        query += ' ORDER BY o.created_at'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def assign_order_to_admin(self, order_id: int, admin_id: int):
        """تعيين طلب لأدمن"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE orders SET admin_assigned = ? WHERE id = ?', (admin_id, order_id))
        self.conn.commit()
    
    # ==================== 💰 دوال طلبات النقاط ====================
    def create_point_request(self, user_id: int, amount: int, proof_text: str = None, proof_image: str = None):
        """إنشاء طلب شحن نقاط"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO point_requests (user_id, amount, proof_text, proof_image, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (user_id, amount, proof_text, proof_image))
        
        request_id = cursor.lastrowid
        self.conn.commit()
        return request_id
    
    def get_pending_point_requests(self):
        """الحصول على طلبات النقاط المعلقة"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT pr.*, u.username, u.first_name 
            FROM point_requests pr 
            JOIN users u ON pr.user_id = u.user_id 
            WHERE pr.status = 'pending' 
            ORDER BY pr.created_at
        ''')
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def approve_point_request(self, request_id: int, admin_notes: str = None):
        """موافقة على طلب نقاط"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT user_id, amount FROM point_requests WHERE id = ?', (request_id,))
        request = cursor.fetchone()
        
        if request:
            user_id, amount = request
            
            cursor.execute('''
                UPDATE point_requests 
                SET status = 'approved', admin_notes = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (admin_notes, request_id))
            
            self.update_user_points(user_id, amount, "add")
            
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message)
                VALUES (?, ?, ?)
            ''', (user_id, "✅ تم شحن نقاطك!", 
                  f"تمت الموافقة على طلبك وتم إضافة {amount} {CURRENCY_SYMBOL} إلى رصيدك."))
            
            self.conn.commit()
            return True
        
        return False
    
    def reject_point_request(self, request_id: int, admin_notes: str = None):
        """رفض طلب نقاط"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE point_requests 
            SET status = 'rejected', admin_notes = ?, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (admin_notes, request_id))
        self.conn.commit()
    
    # ==================== 📊 دوال الإحصائيات ====================
    def get_stats(self):
        """الحصول على إحصائيات البوت"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM users')
        stats['total_users'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(joined_date) = DATE("now")')
        stats['today_users'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE last_active > DATETIME("now", "-1 day")')
        stats['active_users'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products WHERE is_active = 1')
        stats['total_products'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(sold_count) FROM products')
        stats['total_sales'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM orders')
        stats['total_orders'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"')
        stats['pending_orders'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending" AND requires_admin_action = 1')
        stats['pending_admin_orders'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_points) FROM orders WHERE status = "completed"')
        stats['total_revenue'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM point_requests WHERE status = "approved"')
        stats['total_points_added'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM point_requests WHERE status = "pending"')
        stats['pending_point_requests'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM referrals')
        stats['total_referrals'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(points_awarded) FROM referrals')
        stats['referral_points'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM user_ads')
        stats['total_ads'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_ads WHERE status = "pending"')
        stats['pending_ads'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM point_links')
        stats['total_point_links'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM point_links WHERE is_active = 1')
        stats['active_point_links'] = cursor.fetchone()[0]
        
        return stats
    
    # ==================== 🔍 دوال البحث ====================
    def search_products(self, query: str, limit: int = 20):
        """بحث في المنتجات"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.*, c.name as category_name, c.icon as category_icon 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.is_active = 1 AND (p.name LIKE ? OR p.description LIKE ?)
            ORDER BY p.is_featured DESC, p.created_at DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

# ==================== 🎨 نظام الأزرار المتكامل ====================
class CompleteKeyboards:
    def __init__(self, db: CompleteDatabase):
        self.db = db
    
    def main_menu(self, user_id: int):
        """القائمة الرئيسية"""
        is_admin = self.db.is_admin(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🛒 المتجر", callback_data="store"),
             InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
            [InlineKeyboardButton("📦 طلباتي", callback_data="my_orders"),
             InlineKeyboardButton("👥 الإحالات", callback_data="referrals")],
            [InlineKeyboardButton("📤 تحويل نقاط", callback_data="transfer_points"),
             InlineKeyboardButton("📢 نشر إعلان", callback_data="create_ad")],
            [InlineKeyboardButton("📞 التواصل", callback_data="contact"),
             InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        
        if is_admin:
            keyboard.append([
                InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel"),
                InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def store_categories(self):
        """فئات المتجر"""
        categories = self.db.get_categories()
        keyboard = []
        
        for i in range(0, len(categories), 2):
            row = []
            for j in range(2):
                if i + j < len(categories):
                    cat = categories[i + j]
                    button_text = f"{cat['icon']} {cat['name']}"
                    row.append(InlineKeyboardButton(button_text, callback_data=f"cat_{cat['id']}"))
            if row:
                keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("⭐ المنتجات المميزة", callback_data="featured"),
            InlineKeyboardButton("📢 إعلانات المستخدمين", callback_data="user_ads_category")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🔍 بحث", callback_data="search"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def products_list(self, products: List[Dict], show_admin_actions: bool = False, page: int = 0, per_page: int = 10):
        """قائمة المنتجات"""
        keyboard = []
        
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_products = products[start_idx:end_idx]
        
        for product in current_products:
            stock_text = "∞" if product['stock'] == -1 else str(product['stock'])
            admin_text = "👑" if product['requires_admin'] == 1 else ""
            user_ad_text = "📢" if product.get('product_type') == 'user_product' else ""
            
            button_text = f"{user_ad_text}{admin_text} {product['name']} - {CURRENCY_SYMBOL}{product['price']}"
            if product['stock'] == 0:
                button_text += " ⛔"
            
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"prod_{product['id']}")
            ])
        
        total_pages = (len(products) + per_page - 1) // per_page
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"page_{page-1}"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"page_{page+1}"))
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        if show_admin_actions:
            keyboard.append([
                InlineKeyboardButton("✏️ تعديل المنتج", callback_data="admin_edit_product"),
                InlineKeyboardButton("🗑️ حذف المنتج", callback_data="admin_delete_product")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data="store"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def product_detail(self, product: Dict, user_points: int = 0):
        """تفاصيل المنتج"""
        product_id = product['id']
        price = product['price']
        stock = product['stock']
        requires_admin = product['requires_admin'] == 1
        
        keyboard = []
        
        if stock != 0:
            if user_points >= price:
                if requires_admin:
                    keyboard.append([
                        InlineKeyboardButton(f"📞 طلب عبر الأدمن ({CURRENCY_SYMBOL}{price})", 
                                            callback_data=f"buy_admin_{product_id}")
                    ])
                else:
                    keyboard.append([
                        InlineKeyboardButton(f"✅ شراء الآن ({CURRENCY_SYMBOL}{price})", 
                                            callback_data=f"buy_{product_id}")
                    ])
            elif user_points < price:
                keyboard.append([
                    InlineKeyboardButton(f"💰 نقاطك غير كافية ({user_points}/{price})", 
                                        callback_data="balance")
                ])
        
        keyboard.append([
            InlineKeyboardButton("📞 استفسار عن المنتج", 
                                url=f"https://t.me/{ADMIN_CONTACT[1:]}")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data=f"cat_{product['category_id']}"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def transfer_points_keyboard(self):
        """أزرار تحويل النقاط"""
        keyboard = [
            [InlineKeyboardButton("💳 تحويل نقاط", callback_data="start_transfer")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
             InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_ad_keyboard(self):
        """أزرار إنشاء إعلان"""
        keyboard = [
            [InlineKeyboardButton("📢 إنشاء إعلان جديد", callback_data="start_create_ad")],
            [InlineKeyboardButton("📋 إعلاناتي", callback_data="my_ads")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="home")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def admin_panel(self):
        """لوحة تحكم الأدمن"""
        keyboard = []
        
        keyboard.append([
            InlineKeyboardButton("➕ إضافة منتج", callback_data="admin_add_product"),
            InlineKeyboardButton("📦 إدارة المنتجات", callback_data="admin_manage_products")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🛒 طلبات تحتاج متابعة", callback_data="admin_pending_orders"),
            InlineKeyboardButton("📋 جميع الطلبات", callback_data="admin_all_orders")
        ])
        
        keyboard.append([
            InlineKeyboardButton("💰 طلبات شحن النقاط", callback_data="admin_point_requests"),
            InlineKeyboardButton("🎁 إضافة نقاط لمستخدم", callback_data="admin_add_points")
        ])
        
        keyboard.append([
            InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_manage_users"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
        ])
        
        keyboard.append([
            InlineKeyboardButton("📢 إعلانات المستخدمين", callback_data="admin_user_ads"),
            InlineKeyboardButton("🔗 روابط النقاط", callback_data="admin_point_links")
        ])
        
        keyboard.append([
            InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings"),
            InlineKeyboardButton("📢 إرسال إشعار", callback_data="admin_broadcast")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def admin_user_ads_actions(self, ad_id: int):
        """إجراءات الأدمن على إعلان"""
        keyboard = [
            [
                InlineKeyboardButton("✅ قبول الإعلان", callback_data=f"admin_ad_approve_{ad_id}"),
                InlineKeyboardButton("❌ رفض الإعلان", callback_data=f"admin_ad_reject_{ad_id}")
            ],
            [
                InlineKeyboardButton("💰 تعديل السعر", callback_data=f"admin_ad_price_{ad_id}"),
                InlineKeyboardButton("📝 إضافة ملاحظات", callback_data=f"admin_ad_note_{ad_id}")
            ],
            [
                InlineKeyboardButton("🛒 تحويل لمنتج", callback_data=f"admin_ad_to_product_{ad_id}"),
                InlineKeyboardButton("🗑️ حذف الإعلان", callback_data=f"admin_ad_delete_{ad_id}")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_user_ads"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def admin_point_links_actions(self):
        """إجراءات روابط النقاط"""
        keyboard = [
            [
                InlineKeyboardButton("🔗 إنشاء رابط جديد", callback_data="admin_create_point_link"),
                InlineKeyboardButton("📋 الروابط النشطة", callback_data="admin_list_point_links")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def admin_product_actions(self, product_id: int):
        """إجراءات الأدمن على منتج"""
        keyboard = [
            [
                InlineKeyboardButton("✏️ تعديل السعر", callback_data=f"admin_edit_price_{product_id}"),
                InlineKeyboardButton("📦 تعديل المخزون", callback_data=f"admin_edit_stock_{product_id}")
            ],
            [
                InlineKeyboardButton("📝 تعديل الوصف", callback_data=f"admin_edit_desc_{product_id}"),
                InlineKeyboardButton("🔄 تغيير الحالة", callback_data=f"admin_toggle_{product_id}")
            ],
            [
                InlineKeyboardButton("👑 تغيير متابعة الأدمن", callback_data=f"admin_toggle_admin_{product_id}"),
                InlineKeyboardButton("⭐ تغيير التميز", callback_data=f"admin_toggle_featured_{product_id}")
            ],
            [
                InlineKeyboardButton("🗑️ حذف المنتج", callback_data=f"admin_delete_{product_id}"),
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_manage_products")
            ],
            [
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def admin_order_actions(self, order_id: int):
        """إجراءات الأدمن على طلب"""
        keyboard = [
            [
                InlineKeyboardButton("✅ إكمال الطلب", callback_data=f"admin_complete_{order_id}"),
                InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"admin_cancel_{order_id}")
            ],
            [
                InlineKeyboardButton("📞 تواصل مع العميل", callback_data=f"admin_contact_{order_id}"),
                InlineKeyboardButton("📝 إضافة ملاحظات", callback_data=f"admin_note_{order_id}")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_pending_orders"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def payment_methods(self):
        """طرق الحصول على النقاط"""
        keyboard = [
            [
                InlineKeyboardButton("💬 التواصل مع الأدمن", 
                                    url=f"https://t.me/{ADMIN_CONTACT[1:]}")
            ],
            [
                InlineKeyboardButton("🔗 روابط النقاط المؤقتة", callback_data="point_links")
            ],
            [
                InlineKeyboardButton("📢 الحصول من القناة", 
                                    url=CHANNEL_POINTS_LINK)
            ],
            [
                InlineKeyboardButton("👥 نظام الإحالات", callback_data="referral_info"),
                InlineKeyboardButton("💰 رصيدي", callback_data="balance")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="home")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def point_links_keyboard(self):
        """أزرار روابط النقاط"""
        keyboard = [
            [InlineKeyboardButton("🔗 روابط متاحة", callback_data="available_point_links")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def yes_no_keyboard(self, yes_callback: str, no_callback: str):
        """أزرار نعم/لا"""
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم", callback_data=yes_callback),
                InlineKeyboardButton("❌ لا", callback_data=no_callback)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def categories_for_admin(self, action: str = "manage"):
        """فئات للأدمن"""
        categories = self.db.get_categories()
        keyboard = []
        
        for i in range(0, len(categories), 2):
            row = []
            for j in range(2):
                if i + j < len(categories):
                    cat = categories[i + j]
                    button_text = f"{cat['icon']} {cat['name']}"
                    if action == "add_product":
                        row.append(InlineKeyboardButton(button_text, callback_data=f"admin_add_cat_{cat['id']}"))
                    elif action == "manage":
                        row.append(InlineKeyboardButton(button_text, callback_data=f"admin_cat_{cat['id']}"))
            if row:
                keyboard.append(row)
        
        if action == "add_product":
            keyboard.append([
                InlineKeyboardButton("➕ إضافة فئة جديدة", callback_data="admin_new_category"),
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_add_product")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("➕ إضافة فئة جديدة", callback_data="admin_add_category"),
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def confirm_create_point_link(self, points: float, users: int, hours: int):
        """تأكيد إنشاء رابط نقاط"""
        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد إنشاء الرابط", callback_data=f"confirm_link_{points}_{users}_{hours}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="admin_point_links")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

# ==================== 🤖 النظام الرئيسي للبوت ====================
class CompleteTelegramShopBot:
    def __init__(self):
        self.db = CompleteDatabase()
        self.keyboards = CompleteKeyboards(self.db)
        self.application = None
    
    # ==================== ⚡ الأوامر الأساسية ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        referred_by = None
        point_link_code = None
        
        if context.args:
            arg = context.args[0]
            
            if arg.startswith("REF"):
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (arg,))
                    result = cursor.fetchone()
                    if result:
                        referred_by = result[0]
                except:
                    pass
            elif len(arg) >= 12:
                point_link = self.db.get_point_link(arg)
                if point_link:
                    point_link_code = arg
        
        if not self.db.get_user(user.id):
            referral_code = self.db.register_user(user.id, user.username or "", user.first_name, referred_by)
            
            if point_link_code:
                success, message = self.db.use_point_link(point_link_code, user.id)
                if success:
                    await update.message.reply_text(
                        f"🎉 {message}\nمرحباً بك في متجرنا!",
                        parse_mode=ParseMode.HTML
                    )
            
            welcome_text = f"""
🎉 <b>مرحباً {user.first_name} في متجرنا!</b> 🛍️

📢 <b>قناتنا:</b> {REQUIRED_CHANNEL}
👤 <b>للتواصل والشراء:</b> {ADMIN_CONTACT}
💰 <b>للحصول على نقاط:</b> {CHANNEL_POINTS_LINK}

✨ <b>مميزات البوت:</b>
✅ شراء منتجات رقمية بالنقاط
✅ نظام إحالات (كل إحالة = {REFERRAL_POINTS} {CURRENCY_SYMBOL})
✅ تحويل النقاط بين المستخدمين
✅ نشر إعلانات لبيع منتجاتك
✅ دعم فني على مدار الساعة

🎯 <b>رابط الإحالة الخاص بك:</b>
<code>https://t.me/{(await context.bot.get_me()).username}?start={referral_code}</code>

💎 <b>ابدأ رحلتك الآن:</b> 👇
"""
        else:
            if point_link_code:
                success, message = self.db.use_point_link(point_link_code, user.id)
                if success:
                    await update.message.reply_text(
                        f"✅ {message}",
                        parse_mode=ParseMode.HTML
                    )
            
            welcome_text = f"""
<b>مرحباً بعودتك {user.first_name}!</b> 👋

📢 <b>قناتنا:</b> {REQUIRED_CHANNEL}
👤 <b>للتواصل والشراء:</b> {ADMIN_CONTACT}

🎯 <b>اختر من القائمة:</b> 👇
"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.keyboards.main_menu(user.id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    
    async def store_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /store"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        await update.message.reply_text(
            "<b>🛒 المتجر الإلكتروني</b>\n\n<b>📁 اختر الفئة المناسبة:</b>",
            reply_markup=self.keyboards.store_categories(),
            parse_mode=ParseMode.HTML
        )
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /balance"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        user_data = self.db.get_user(user.id)
        if not user_data:
            await update.message.reply_text("⚠️ يجب استخدام /start أولاً")
            return
        
        points = user_data['points']
        total_earned = user_data['total_earned']
        total_spent = user_data['total_spent']
        
        balance_text = f"""
<b>💰 رصيد النقاط</b>

⭐ <b>النقاط الحالية:</b> {points} {CURRENCY_SYMBOL}
📈 <b>إجمالي المكتسب:</b> {total_earned} {CURRENCY_SYMBOL}
📉 <b>إجمالي المنفق:</b> {total_spent} {CURRENCY_SYMBOL}

💸 <b>طرق الحصول على النقاط:</b>
"""
        
        await update.message.reply_text(
            balance_text,
            reply_markup=self.keyboards.payment_methods(),
            parse_mode=ParseMode.HTML
        )
    
    async def transfer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /transfer"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        user_data = self.db.get_user(user.id)
        if not user_data:
            await update.message.reply_text("⚠️ يجب استخدام /start أولاً")
            return
        
        await update.message.reply_text(
            "<b>📤 تحويل النقاط</b>\n\n"
            "يمكنك تحويل نقاطك إلى مستخدمين آخرين.\n\n"
            "<b>طريقة الاستخدام:</b>\n"
            "1. اضغط على زر 'تحويل نقاط'\n"
            "2. أرسل معرف المستخدم (User ID)\n"
            "3. أرسل عدد النقاط\n\n"
            "ملاحظة: يجب أن يكون المستخدم موجوداً في البوت",
            reply_markup=self.keyboards.transfer_points_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    async def create_ad_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /ad"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        user_data = self.db.get_user(user.id)
        if not user_data:
            await update.message.reply_text("⚠️ يجب استخدام /start أولاً")
            return
        
        await update.message.reply_text(
            "<b>📢 نظام الإعلانات</b>\n\n"
            "يمكنك نشر إعلان لبيع منتجاتك:\n\n"
            "<b>المتطلبات:</b>\n"
            "• عنوان واضح\n"
            "• وصف مفصل\n"
            "• سعر مناسب\n"
            "• صور أو فيديو (3 كحد أقصى)\n\n"
            "<b>ملاحظة:</b>\n"
            "سيقوم الأدمن بمراجعة إعلانك\n"
            "وقد يقوم بتعديل السعر قبل الموافقة",
            reply_markup=self.keyboards.create_ad_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    async def my_ads_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /myads"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        ads = self.db.get_user_ads(user.id)
        
        if not ads:
            await update.message.reply_text(
                "<b>📭 لا توجد إعلانات</b>\n\nلم تنشر أي إعلانات بعد.",
                reply_markup=self.keyboards.create_ad_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        ads_text = "<b>📋 إعلاناتك</b>\n\n"
        
        for ad in ads[:5]:
            status_icon = "✅" if ad['status'] == 'approved' else "⏳" if ad['status'] == 'pending' else "❌"
            price = ad['final_price'] or ad['price']
            
            ads_text += f"""
{status_icon} <b>{ad['title']}</b>
💰 <b>السعر:</b> {price} {CURRENCY_SYMBOL}
📊 <b>الحالة:</b> {ad['status']}
📅 <b>التاريخ:</b> {ad['created_at'][:16]}
━━━━━━━━━━━━━━━━━━━━
"""
        
        await update.message.reply_text(
            ads_text,
            reply_markup=self.keyboards.create_ad_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    async def id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /id"""
        user = update.effective_user
        await update.message.reply_text(
            f"<b>🆔 معرفك:</b> <code>{user.id}</code>\n\n"
            "يمكنك مشاركة هذا المعرف مع الآخرين\n"
            "لتحويل النقاط إليك.",
            parse_mode=ParseMode.HTML
        )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /search"""
        user = update.effective_user
        self.db.update_last_active(user.id)
        
        if not context.args:
            await update.message.reply_text(
                "🔍 <b>البحث في المتجر</b>\n\n"
                "استخدم: /search كلمة البحث\n"
                "مثال: /search نتفليكس",
                parse_mode=ParseMode.HTML
            )
            return
        
        search_query = ' '.join(context.args)
        products = self.db.search_products(search_query)
        
        if not products:
            await update.message.reply_text(
                f"❌ <b>لا توجد نتائج للبحث عن:</b> {search_query}\n\n"
                "جرب كلمات بحث أخرى أو تصفح المتجر.",
                reply_markup=self.keyboards.store_categories(),
                parse_mode=ParseMode.HTML
            )
            return
        
        products_text = f"🔍 <b>نتائج البحث عن:</b> {search_query}\n\n"
        
        for product in products[:10]:
            stock_text = "∞" if product['stock'] == -1 else str(product['stock'])
            admin_icon = "👑" if product['requires_admin'] == 1 else ""
            featured_icon = "⭐" if product['is_featured'] == 1 else ""
            
            products_text += f"{featured_icon}{admin_icon} <b>{product['name']}</b>\n"
            products_text += f"💰 {CURRENCY_SYMBOL}{product['price']} | 📦 {stock_text} | 🏷️ {product['category_name']}\n"
            products_text += f"<code>/start prod_{product['id']}</code>\n━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = []
        for i in range(0, min(len(products), 5), 2):
            row = []
            for j in range(2):
                if i + j < len(products):
                    product = products[i + j]
                    row.append(InlineKeyboardButton(
                        f"{product['name'][:15]}...",
                        callback_data=f"prod_{product['id']}"
                    ))
            if row:
                keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("🛒 عرض الكل", callback_data="store"),
            InlineKeyboardButton("🔍 بحث جديد", callback_data="search")
        ])
        
        await update.message.reply_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # ==================== 🔘 معالجات الأزرار ====================
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة جميع نقرات الأزرار"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        self.db.update_last_active(user.id)
        
        # معالجة مراجعة الإعلانات
        if data.startswith("admin_ad_review_"):
            ad_id = int(data.split("_")[3])
            await self.show_admin_ad_detail(update, context, ad_id)
            return
            
        # معالجة تأكيد إنشاء رابط نقاط
        if data.startswith("confirm_link_"):
            await self.handle_confirm_point_link(update, context)
            return
        
        if data == "home":
            await self.show_home(update, context)
        elif data == "store":
            await self.show_store(update, context)
        elif data.startswith("cat_"):
            await self.show_category_products(update, context)
        elif data == "user_ads_category":
            await self.show_user_ads_category(update, context)
        elif data.startswith("prod_"):
            await self.show_product_details(update, context)
        elif data.startswith("buy_"):
            await self.handle_purchase(update, context)
        elif data == "balance":
            await self.show_balance(update, context)
        elif data == "my_orders":
            await self.show_user_orders(update, context)
        elif data == "referrals":
            await self.show_referrals(update, context)
        elif data == "contact":
            await self.show_contact(update, context)
        elif data == "transfer_points":
            await self.start_transfer_points(update, context)
        elif data == "create_ad":
            await self.show_create_ad_menu(update, context)
        elif data == "my_ads":
            await self.show_my_ads(update, context)
        elif data == "start_create_ad":
            await self.start_create_ad(update, context)
        elif data == "point_links":
            await self.show_point_links(update, context)
        elif data == "available_point_links":
            await self.show_available_point_links(update, context)
        elif data == "admin_panel":
            await self.show_admin_panel(update, context)
        elif data.startswith("admin_"):
            await self.handle_admin_actions(update, context)
        elif data.startswith("page_"):
            await self.handle_pagination(update, context)
        elif data == "search":
            await self.start_search(update, context)
        elif data == "featured":
            await self.show_featured_products(update, context)
        elif data == "settings":
            await self.show_settings(update, context)
        elif data == "referral_info":
            await self.show_referrals(update, context)
        else:
            await query.edit_message_text("⏳ هذه الميزة قيد التطوير!")
    
    async def handle_confirm_point_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة تأكيد إنشاء رابط نقاط"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        parts = data.split("_")
        
        # استخراج البيانات من callback_data
        if len(parts) >= 4:
            try:
                points = float(parts[2])
                users = int(parts[3])
                hours = int(parts[4])
                
                user = query.from_user
                link_id, link_code = self.db.create_point_link(user.id, points, users, hours)
                
                link_url = f"https://t.me/{(await context.bot.get_me()).username}?start={link_code}"
                
                success_text = f"""
<b>✅ تم إنشاء رابط النقاط بنجاح!</b>

<b>🔗 الرابط:</b> <code>{link_url}</code>
<b>💰 النقاط لكل مستخدم:</b> {points} {CURRENCY_SYMBOL}
<b>👥 الحد الأقصى:</b> {users} مستخدم
<b>⏰ الصلاحية:</b> {hours} ساعة
<b>🆔 كود الرابط:</b> <code>{link_code}</code>
"""
                
                await query.edit_message_text(
                    success_text,
                    reply_markup=self.keyboards.admin_panel(),
                    parse_mode=ParseMode.HTML
                )
                return
            except Exception as e:
                logger.error(f"خطأ في إنشاء رابط النقاط: {e}")
        
        await query.edit_message_text(
            "❌ حدث خطأ في إنشاء الرابط",
            reply_markup=self.keyboards.admin_panel(),
            parse_mode=ParseMode.HTML
        )
    
    # ==================== 🛒 دوال المتجر ====================
    async def show_home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الصفحة الرئيسية"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        await query.edit_message_text(
            "<b>🏠 الصفحة الرئيسية</b>",
            reply_markup=self.keyboards.main_menu(user.id),
            parse_mode=ParseMode.HTML
        )
    
    async def show_store(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض المتجر"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "<b>🛒 المتجر الإلكتروني</b>\n\n<b>📁 اختر الفئة المناسبة:</b>",
            reply_markup=self.keyboards.store_categories(),
            parse_mode=ParseMode.HTML
        )
    
    async def show_category_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض منتجات الفئة"""
        query = update.callback_query
        await query.answer()
        
        try:
            category_id = int(query.data.split("_")[1])
        except:
            category_id = int(context.user_data.get('current_category', 1))
        
        category = self.db.get_category(category_id)
        
        if not category:
            await query.edit_message_text("❌ الفئة غير موجودة")
            return
        
        products = self.db.get_products(category_id=category_id)
        
        if not products:
            await query.edit_message_text(
                f"<b>📭 {category['icon']} {category['name']}</b>\n\nلا توجد منتجات في هذه الفئة حالياً.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="store"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
                ]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        context.user_data['current_category'] = category_id
        
        page = 0
        if 'page' in context.user_data:
            page = context.user_data['page']
        
        products_text = f"<b>🛍️ {category['icon']} {category['name']}</b>\n\n"
        products_text += f"<i>{category['description']}</i>\n\n"
        products_text += f"<b>المنتجات المتاحة ({len(products)}):</b>\n"
        
        await query.edit_message_text(
            products_text,
            reply_markup=self.keyboards.products_list(products, page=page),
            parse_mode=ParseMode.HTML
        )
    
    async def show_user_ads_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إعلانات المستخدمين"""
        query = update.callback_query
        await query.answer()
        
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT id FROM categories WHERE name LIKE ?', ("%إعلانات المستخدمين%",))
        category = cursor.fetchone()
        
        if category:
            category_id = category[0]
            products = self.db.get_products(category_id=category_id)
            
            if products:
                await self.show_category_products(update, context)
                return
        
        await query.edit_message_text(
            "<b>📢 إعلانات المستخدمين</b>\n\n"
            "يمكنك نشر إعلان لبيع منتجاتك.\n"
            "سيقوم الأدمن بمراجعة إعلانك والموافقة عليه.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 نشر إعلان", callback_data="create_ad"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]]),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_pagination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة التصفح بين الصفحات"""
        query = update.callback_query
        await query.answer()
        
        page = int(query.data.split("_")[1])
        context.user_data['page'] = page
        
        await self.show_category_products(update, context)
    
    async def show_product_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض تفاصيل المنتج"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split("_")[1])
        product = self.db.get_product(product_id)
        
        if not product:
            await query.edit_message_text("❌ المنتج غير موجود")
            return
        
        user_data = self.db.get_user(query.from_user.id)
        user_points = user_data['points'] if user_data else 0
        
        stock_text = "∞" if product['stock'] == -1 else str(product['stock'])
        admin_text = "\n👑 <b>يتطلب متابعة أدمن</b>" if product['requires_admin'] == 1 else ""
        user_ad_text = "\n📢 <b>منتج من مستخدم</b>" if product.get('product_type') == 'user_product' else ""
        
        product_text = f"""
<b>🎯 {product['name']}</b>{user_ad_text}

💰 <b>السعر:</b> {product['price']} {CURRENCY_SYMBOL}
📦 <b>المخزون:</b> {stock_text}
🏷️ <b>النوع:</b> {product['product_type']}
📋 <b>التسليم:</b> {product['delivery_type']}{admin_text}

<b>📝 الوصف:</b>
{product['description']}

🆔 <b>الكود:</b> #{product['id']}
"""
        
        if user_points < product['price']:
            product_text += f"\n⚠️ <b>نقاطك غير كافية</b> ({user_points}/{product['price']} {CURRENCY_SYMBOL})"
        
        await query.edit_message_text(
            product_text,
            reply_markup=self.keyboards.product_detail(product, user_points),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة عملية الشراء"""
        query = update.callback_query
        await query.answer()
        
        data_parts = query.data.split("_")
        product_id = int(data_parts[1])
        
        product = self.db.get_product(product_id)
        user = query.from_user
        user_data = self.db.get_user(user.id)
        
        if not product or not user_data:
            await query.edit_message_text("❌ حدث خطأ، حاول مرة أخرى")
            return
        
        if product['stock'] == 0:
            await query.edit_message_text("⛔ المنتج نفذ من المخزون")
            return
        
        if user_data['points'] < product['price'] and user_data.get('unlimited_points') != 1:
            await query.edit_message_text(
                f"<b>⚠️ نقاطك غير كافية!</b>\n\n"
                f"💰 <b>السعر:</b> {product['price']} {CURRENCY_SYMBOL}\n"
                f"💳 <b>نقاطك:</b> {user_data['points']} {CURRENCY_SYMBOL}\n\n"
                f"💸 <b>لشحن النقاط:</b>\n"
                f"1. تواصل مع {ADMIN_CONTACT}\n"
                f"2. أو احصل على نقاط من {CHANNEL_POINTS_LINK}",
                parse_mode=ParseMode.HTML
            )
            return
        
        order_id, order_code, total_points = self.db.create_order(user.id, product_id)
        
        if not order_id:
            await query.edit_message_text("❌ فشل إنشاء الطلب، حاول مرة أخرى")
            return
        
        if user_data.get('unlimited_points') != 1:
            self.db.update_user_points(user.id, total_points, "subtract")
        
        self.db.update_product_stock(product_id, 1)
        
        success_text = f"""
<b>✅ تم إنشاء الطلب بنجاح!</b>

🛒 <b>المنتج:</b> {product['name']}
💰 <b>المبلغ:</b> {total_points} {CURRENCY_SYMBOL}
📦 <b>رقم الطلب:</b> <code>{order_code}</code>

"""
        
        if product['requires_admin'] == 1:
            success_text += f"""
<b>👑 هذا المنتج يتطلب متابعة أدمن</b>

<b>📞 الخطوات التالية:</b>
1. تواصل مع الأدمن: {ADMIN_CONTACT}
2. أرسل له رقم طلبك: <code>{order_code}</code>
3. انتظر تسليم المنتج من الأدمن

⏱️ <b>وقت الاستجابة:</b> 5-15 دقيقة
"""
        else:
            delivery_data = self.generate_delivery_data(product)
            self.db.complete_order(order_id, delivery_data)
            
            success_text += f"""
<b>🎁 بيانات المنتج:</b>
{delivery_data}

💾 <b>نصيحة:</b> احفظ هذه البيانات في مكان آمن.
"""
        
        success_text += f"\n📞 <b>للإستفسار:</b> {ADMIN_CONTACT}"
        
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.HTML
        )
        
        if product['requires_admin'] == 1 and self.db.is_admin(ADMIN_ID):
            admin_notice = f"""
<b>👑 طلب جديد يحتاج متابعة!</b>

👤 <b>المشتري:</b> {user.first_name} (@{user.username or 'لا يوجد'})
🛒 <b>المنتج:</b> {product['name']}
💰 <b>النقاط:</b> {total_points} {CURRENCY_SYMBOL}
📦 <b>رقم الطلب:</b> <code>{order_code}</code>

📞 <b>للتواصل مع العميل:</b>
<a href='tg://user?id={user.id}'>اضغط هنا</a>
"""
            
            await context.bot.send_message(
                ADMIN_ID,
                admin_notice,
                parse_mode=ParseMode.HTML
            )
    
    def generate_delivery_data(self, product: Dict) -> str:
        """توليد بيانات تسليم المنتج"""
        product_type = product['product_type']
        
        if product_type == "account":
            username = f"user{random.randint(100000, 999999)}"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            return f"👤 <b>المستخدم:</b> <code>{username}</code>\n🔐 <b>كلمة المرور:</b> <code>{password}</code>"
        
        elif product_type == "app" or product_type == "software":
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            return f"🔓 <b>كود التفعيل:</b> <code>{code}</code>"
        
        else:
            return "📦 <b>سيتم إرسال البيانات خلال 5 دقائق</b>\n\n📞 <b>إذا لم تصلك البيانات خلال 10 دقائق، تواصل مع:</b> " + ADMIN_CONTACT
    
    async def show_featured_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض المنتجات المميزة"""
        query = update.callback_query
        await query.answer()
        
        products = self.db.get_products(featured_only=True)
        
        if not products:
            await query.edit_message_text(
                "<b>⭐ لا توجد منتجات مميزة حالياً</b>",
                reply_markup=self.keyboards.store_categories(),
                parse_mode=ParseMode.HTML
            )
            return
        
        products_text = "<b>⭐ المنتجات المميزة</b>\n\n"
        
        for product in products[:10]:
            stock_text = "∞" if product['stock'] == -1 else str(product['stock'])
            admin_icon = "👑" if product['requires_admin'] == 1 else ""
            products_text += f"⭐{admin_icon} <b>{product['name']}</b>\n"
            products_text += f"💰 {CURRENCY_SYMBOL}{product['price']} | 📦 {stock_text} | 🏷️ {product['category_name']}\n"
            products_text += f"<code>/start prod_{product['id']}</code>\n━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = []
        for i in range(0, min(len(products), 6), 2):
            row = []
            for j in range(2):
                if i + j < len(products):
                    product = products[i + j]
                    row.append(InlineKeyboardButton(
                        f"⭐ {product['name'][:15]}...",
                        callback_data=f"prod_{product['id']}"
                    ))
            if row:
                keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("🛒 عرض الكل", callback_data="store"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        await query.edit_message_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def start_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء البحث"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔍 <b>البحث في المتجر</b>\n\n"
            "أرسل كلمة البحث:\n\n"
            "<i>مثال: نتفليكس، سبوتيفاي، ألعاب</i>",
            parse_mode=ParseMode.HTML
        )
        context.user_data['searching'] = True
        return SEARCH_QUERY
    
    async def process_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة البحث"""
        user = update.effective_user
        search_query = update.message.text
        
        products = self.db.search_products(search_query)
        
        if not products:
            await update.message.reply_text(
                f"❌ <b>لا توجد نتائج للبحث عن:</b> {search_query}\n\n"
                "جرب كلمات بحث أخرى أو تصفح المتجر.",
                reply_markup=self.keyboards.store_categories(),
                parse_mode=ParseMode.HTML
            )
            context.user_data.pop('searching', None)
            return
        
        products_text = f"🔍 <b>نتائج البحث عن:</b> {search_query}\n\n"
        
        for product in products[:10]:
            stock_text = "∞" if product['stock'] == -1 else str(product['stock'])
            admin_icon = "👑" if product['requires_admin'] == 1 else ""
            featured_icon = "⭐" if product['is_featured'] == 1 else ""
            
            products_text += f"{featured_icon}{admin_icon} <b>{product['name']}</b>\n"
            products_text += f"💰 {CURRENCY_SYMBOL}{product['price']} | 📦 {stock_text} | 🏷️ {product['category_name']}\n"
            products_text += f"<code>/start prod_{product['id']}</code>\n━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = []
        for i in range(0, min(len(products), 5), 2):
            row = []
            for j in range(2):
                if i + j < len(products):
                    product = products[i + j]
                    row.append(InlineKeyboardButton(
                        f"{product['name'][:15]}...",
                        callback_data=f"prod_{product['id']}"
                    ))
            if row:
                keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("🛒 عرض الكل", callback_data="store"),
            InlineKeyboardButton("🔍 بحث جديد", callback_data="search")
        ])
        
        await update.message.reply_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        context.user_data.pop('searching', None)
    
    # ==================== 💰 دوال الرصيد ====================
    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض رصيد المستخدم"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        
        if not user_data:
            await query.edit_message_text("⚠️ يجب استخدام /start أولاً")
            return
        
        stats = self.db.get_user_stats(user.id)
        
        balance_text = f"""
<b>💰 رصيد النقاط الشخصي</b>

⭐ <b>النقاط الحالية:</b> {user_data['points']} {CURRENCY_SYMBOL}
{"♾️ <b>لديك نقاط غير محدودة</b>" if user_data.get('unlimited_points') == 1 else ""}

<b>📊 إحصائياتك:</b>
🛒 <b>إجمالي المشتريات:</b> {stats['total_purchases']} {CURRENCY_SYMBOL}
📦 <b>عدد الطلبات:</b> {stats['total_orders']}
✅ <b>الطلبات المكتملة:</b> {stats['completed_orders']}
👥 <b>الإحالات النشطة:</b> {stats['active_referrals']}

📈 <b>إجمالي المكتسب:</b> {user_data['total_earned']} {CURRENCY_SYMBOL}
📉 <b>إجمالي المنفق:</b> {user_data['total_spent']} {CURRENCY_SYMBOL}

<b>💸 طرق الحصول على النقاط:</b>
"""
        
        await query.edit_message_text(
            balance_text,
            reply_markup=self.keyboards.payment_methods(),
            parse_mode=ParseMode.HTML
        )
    
    async def show_referrals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض نظام الإحالات"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        
        if not user_data:
            await query.edit_message_text("⚠️ يجب استخدام /start أولاً")
            return
        
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_data['referral_code']}"
        
        referrals_text = f"""
<b>👥 نظام الإحالات</b>

🎁 <b>مكافأة كل إحالة:</b> {REFERRAL_POINTS} {CURRENCY_SYMBOL}
<b>📊 إحصائياتك:</b>
👥 <b>عدد الإحالات:</b> {user_data['referrals_count']}
💰 <b>نقاط الإحالات:</b> {user_data['referrals_earned']} {CURRENCY_SYMBOL}

🔗 <b>رابط الإحالة الخاص بك:</b>
<code>{referral_link}</code>

<b>📋 كيفية العمل:</b>
1. شارك رابطك مع أصدقائك
2. عندما يسجلون عبر رابطك
3. تحصل أنت وصديقك على {REFERRAL_POINTS} {CURRENCY_SYMBOL} لكل واحد

🎯 <b>نصيحة:</b> شارك الرابط في القنات والمجموعات!
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 مشاركة الرابط", 
                                 url=f"https://t.me/share/url?url={referral_link}&text=انضم%20إلى%20متجرنا%20للحصول%20على%20منتجات%20رقمية%20رائعة!")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
             InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
        ])
        
        await query.edit_message_text(
            referrals_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def show_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض معلومات التواصل"""
        query = update.callback_query
        await query.answer()
        
        contact_text = f"""
<b>📞 معلومات التواصل</b>

👤 <b>للتواصل والبيع:</b> {ADMIN_CONTACT}
📢 <b>القناة الرسمية:</b> {REQUIRED_CHANNEL}
💰 <b>للحصول على نقاط:</b> {CHANNEL_POINTS_LINK}

🕒 <b>أوقات العمل:</b> 24/7
⚡ <b>وقت الاستجابة:</b> 5-15 دقيقة

<b>📋 خدماتنا:</b>
• شراء نقاط للبوت
• استفسارات عن المنتجات
• مشاكل في الطلبات
• مقترحات وتطوير

<b>📞 للتواصل السريع:</b>
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 تواصل مع الأدمن", 
                                 url=f"https://t.me/{ADMIN_CONTACT[1:]}")],
            [InlineKeyboardButton("📢 انضم للقناة", 
                                 url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton("💰 للحصول على نقاط", 
                                 url=CHANNEL_POINTS_LINK)],
            [InlineKeyboardButton("🔙 رجوع", callback_data="home")]
        ])
        
        await query.edit_message_text(
            contact_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    
    async def show_user_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض طلبات المستخدم"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        orders = self.db.get_user_orders(user.id)
        
        if not orders:
            await query.edit_message_text(
                "<b>📭 لا توجد طلبات سابقة</b>\n\nلم تقم بأي عملية شراء بعد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🛒 ابدأ التسوق", callback_data="store"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
                ]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        orders_text = "<b>📦 طلباتك السابقة</b>\n\n"
        
        for order in orders[:5]:
            status_icon = "✅" if order['status'] == 'completed' else "⏳" if order['status'] == 'pending' else "❌"
            admin_icon = "👑" if order['requires_admin_action'] == 1 else ""
            
            orders_text += f"""
{status_icon} <b>الطلب:</b> <code>{order['order_code']}</code>
🛒 <b>المنتج:</b> {order['product_name']}
💰 <b>النقاط:</b> {order['total_points']} {CURRENCY_SYMBOL}
📅 <b>التاريخ:</b> {order['created_at'][:16]}
{admin_icon} <b>الحالة:</b> {order['status']}
━━━━━━━━━━━━━━━━━━━━
"""
        
        await query.edit_message_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 متابعة التسوق", callback_data="store"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]]),
            parse_mode=ParseMode.HTML
        )
    
    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الإعدادات"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        settings_text = f"""
<b>⚙️ إعدادات البوت</b>

👤 <b>معلومات حسابك:</b>
🆔 <b>المعرف:</b> <code>{user.id}</code>
📅 <b>تاريخ التسجيل:</b> {self.db.get_user(user.id)['joined_date'][:10] if self.db.get_user(user.id) else 'غير معروف'}

🔔 <b>إشعارات:</b> ✅ مفعلة
🌐 <b>اللغة:</b> العربية

🔒 <b>خصوصية:</b>
• يمكن للآخرين رؤية اسمك فقط
• لا يمكنهم رؤية نقاطك
• يمكن تحويل النقاط إليك عبر المعرف

<b>📞 للدعم الفني:</b> {ADMIN_CONTACT}
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث البيانات", callback_data="refresh_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="home"),
             InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
        ])
        
        await query.edit_message_text(
            settings_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    # ==================== 📤 دوال تحويل النقاط ====================
    async def start_transfer_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية تحويل النقاط"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        
        if not user_data:
            await query.answer("⚠️ يجب استخدام /start أولاً", show_alert=True)
            return
        
        context.user_data['transfer_step'] = 1
        
        await query.edit_message_text(
            "<b>📤 تحويل النقاط - الخطوة 1</b>\n\n"
            "<b>أرسل معرف المستخدم (User ID) الذي تريد تحويل النقاط إليه:</b>\n\n"
            f"<b>💳 رصيدك الحالي:</b> {user_data['points']} {CURRENCY_SYMBOL}\n"
            "<i>ملاحظة: يمكن للمستلم معرفة ID الخاص به باستخدام /id</i>",
            parse_mode=ParseMode.HTML
        )
        return TRANSFER_POINTS_USER
    
    async def process_transfer_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة تحويل النقاط"""
        user = update.effective_user
        message_text = update.message.text
        
        if context.user_data.get('transfer_step') == 1:
            try:
                to_user_id = int(message_text)
                
                to_user = self.db.get_user(to_user_id)
                if not to_user:
                    await update.message.reply_text("❌ المستخدم غير موجود")
                    return TRANSFER_POINTS_USER
                
                if to_user_id == user.id:
                    await update.message.reply_text("❌ لا يمكن تحويل النقاط لنفسك")
                    return TRANSFER_POINTS_USER
                
                context.user_data['transfer_to_user'] = to_user_id
                context.user_data['transfer_step'] = 2
                
                user_data = self.db.get_user(user.id)
                
                await update.message.reply_text(
                    f"<b>📤 تحويل النقاط - الخطوة 2</b>\n\n"
                    f"👤 <b>المستلم:</b> {to_user['first_name']} (@{to_user['username'] or 'لا يوجد'})\n"
                    f"💳 <b>رصيدك الحالي:</b> {user_data['points']} {CURRENCY_SYMBOL}\n\n"
                    f"<b>أرسل عدد النقاط المطلوب تحويلها:</b>",
                    parse_mode=ParseMode.HTML
                )
                return TRANSFER_POINTS_AMOUNT
                
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال معرف مستخدم صحيح (أرقام فقط)")
                return TRANSFER_POINTS_USER
        
        elif context.user_data.get('transfer_step') == 2:
            try:
                amount = int(message_text)
                
                if amount <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال عدد نقاط صحيح أكبر من صفر")
                    return TRANSFER_POINTS_AMOUNT
                
                to_user_id = context.user_data.get('transfer_to_user')
                
                success, message = self.db.transfer_points(user.id, to_user_id, amount)
                
                if success:
                    await update.message.reply_text(
                        f"✅ <b>تم التحويل بنجاح!</b>\n\n"
                        f"💰 <b>المبلغ:</b> {amount} {CURRENCY_SYMBOL}\n"
                        f"👤 <b>المستلم:</b> #{to_user_id}\n\n"
                        f"📞 <b>لأي استفسار:</b> {ADMIN_CONTACT}",
                        reply_markup=self.keyboards.main_menu(user.id),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.message.reply_text(
                        f"❌ <b>فشل التحويل:</b>\n{message}",
                        reply_markup=self.keyboards.main_menu(user.id),
                        parse_mode=ParseMode.HTML
                    )
                
                del context.user_data['transfer_step']
                del context.user_data['transfer_to_user']
                return ConversationHandler.END
                
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال عدد نقاط صحيح (أرقام فقط)")
                return TRANSFER_POINTS_AMOUNT
    
    # ==================== 📢 دوال الإعلانات ====================
    async def show_create_ad_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة إنشاء الإعلان"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "<b>📢 نظام الإعلانات</b>\n\n"
            "يمكنك نشر إعلان لبيع منتجاتك:\n\n"
            "<b>المتطلبات:</b>\n"
            "• عنوان واضح\n"
            "• وصف مفصل\n"
            "• سعر مناسب\n"
            "• صور أو فيديو (3 كحد أقصى)\n\n"
            "<b>ملاحظة:</b>\n"
            "سيقوم الأدمن بمراجعة إعلانك\n"
            "وقد يقوم بتعديل السعر قبل الموافقة",
            reply_markup=self.keyboards.create_ad_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    async def start_create_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إنشاء إعلان"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        context.user_data['create_ad_step'] = 1
        context.user_data['ad_images'] = []
        
        await query.edit_message_text(
            "<b>📢 إنشاء إعلان جديد - الخطوة 1</b>\n\n<b>أرسل عنوان الإعلان:</b>\n<i>مثال: حساب نتفليكس بريميوم لمدة شهر</i>",
            parse_mode=ParseMode.HTML
        )
        return ADD_AD_TITLE
    
    async def process_create_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إنشاء الإعلان"""
        user = update.effective_user
        message_text = update.message.text
        
        if context.user_data.get('create_ad_step') == 1:
            context.user_data['ad_title'] = message_text
            context.user_data['create_ad_step'] = 2
            
            await update.message.reply_text(
                f"<b>📢 إنشاء إعلان جديد - الخطوة 2</b>\n\n"
                f"<b>العنوان:</b> {message_text}\n\n"
                f"<b>أرسل وصف الإعلان:</b>\n"
                f"<i>اشرح المنتج بشكل مفصل</i>",
                parse_mode=ParseMode.HTML
            )
            return ADD_AD_DESC
        
        elif context.user_data.get('create_ad_step') == 2:
            context.user_data['ad_desc'] = message_text
            context.user_data['create_ad_step'] = 3
            
            await update.message.reply_text(
                f"<b>📢 إنشاء إعلان جديد - الخطوة 3</b>\n\n"
                f"<b>العنوان:</b> {context.user_data['ad_title']}\n"
                f"<b>الوصف:</b> {message_text[:50]}...\n\n"
                f"<b>أرسل سعر المنتج (بالنقاط):</b>",
                parse_mode=ParseMode.HTML
            )
            return ADD_AD_PRICE
        
        elif context.user_data.get('create_ad_step') == 3:
            try:
                price = float(message_text)
                if price <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال سعر صحيح أكبر من صفر")
                    return ADD_AD_PRICE
                
                context.user_data['ad_price'] = price
                context.user_data['create_ad_step'] = 4
                
                await update.message.reply_text(
                    f"<b>📢 إنشاء إعلان جديد - الخطوة 4</b>\n\n"
                    f"<b>العنوان:</b> {context.user_data['ad_title']}\n"
                    f"<b>السعر:</b> {price} {CURRENCY_SYMBOL}\n\n"
                    f"<b>أرسل الآن صور المنتج (3 كحد أقصى):</b>\n"
                    f"<i>يمكنك تخطي هذه الخطوة بالضغط على /skip</i>\n"
                    f"<i>أو أرسل /done عندما تنتهي</i>",
                    parse_mode=ParseMode.HTML
                )
                return ADD_AD_IMAGES
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال سعر صحيح (أرقام فقط)")
                return ADD_AD_PRICE
    
    async def process_ad_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة صور الإعلان"""
        user = update.effective_user
        
        if context.user_data.get('create_ad_step') != 4:
            return
        
        if update.message.photo:
            photo = update.message.photo[-1]
            context.user_data['ad_images'].append(photo.file_id)
            
            images_count = len(context.user_data['ad_images'])
            
            if images_count >= 3:
                await update.message.reply_text(
                    f"✅ تم استلام {images_count} صور\nتم الوصول للحد الأقصى من الصور، جاري إنهاء الإعلان..."
                )
                return await self.finalize_ad(update, context)
            else:
                await update.message.reply_text(
                    f"✅ تم استلام الصورة {images_count}\n"
                    f"يمكنك إرسال {3-images_count} صور إضافية\n"
                    "أو اضغط على /done للمتابعة"
                )
        elif update.message.video:
            video = update.message.video
            context.user_data['ad_images'].append(video.file_id)
            
            await update.message.reply_text(
                "✅ تم استلام الفيديو\nاضغط على /done للمتابعة"
            )
        return ADD_AD_IMAGES
    
    async def skip_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تخطي إضافة صور"""
        return await self.finalize_ad(update, context)
    
    async def done_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنهاء إضافة الصور"""
        return await self.finalize_ad(update, context)
    
    async def finalize_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنهاء إنشاء الإعلان"""
        user = update.effective_user
        
        title = context.user_data.get('ad_title')
        desc = context.user_data.get('ad_desc')
        price = context.user_data.get('ad_price')
        images = context.user_data.get('ad_images', [])
        
        images_json = json.dumps(images)
        
        ad_id = self.db.create_user_ad(user.id, title, desc, price, images_json)
        
        confirm_text = f"""
<b>📢 تم إنشاء الإعلان بنجاح!</b>

<b>🆔 رقم الإعلان:</b> #{ad_id}
<b>📌 العنوان:</b> {title}
<b>💰 السعر:</b> {price} {CURRENCY_SYMBOL}
<b>📝 الوصف:</b> {desc[:100]}...
<b>📸 الصور:</b> {len(images)} صورة/فيديو

<b>⏳ الحالة:</b> قيد المراجعة
<b>📞 للأدمن:</b> {ADMIN_CONTACT}

<b>ملاحظة:</b>
سيقوم الأدمن بمراجعة إعلانك
وقد يقوم بتعديل السعر قبل الموافقة
"""
        
        await update.message.reply_text(
            confirm_text,
            reply_markup=self.keyboards.main_menu(user.id),
            parse_mode=ParseMode.HTML
        )
        
        if self.db.is_admin(ADMIN_ID):
            admin_notice = f"""
<b>📢 إعلان جديد يحتاج مراجعة!</b>

<b>🆔 رقم الإعلان:</b> #{ad_id}
<b>👤 الناشر:</b> {user.first_name} (@{user.username or 'لا يوجد'})
<b>📌 العنوان:</b> {title}
<b>💰 السعر المقترح:</b> {price} {CURRENCY_SYMBOL}

<b>📞 للتواصل مع الناشر:</b>
<a href='tg://user?id={user.id}'>اضغط هنا</a>
"""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 مراجعة الإعلان", callback_data=f"admin_ad_review_{ad_id}")]
            ])
            
            await context.bot.send_message(
                ADMIN_ID,
                admin_notice,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        
        del context.user_data['create_ad_step']
        del context.user_data['ad_title']
        del context.user_data['ad_desc']
        del context.user_data['ad_price']
        del context.user_data['ad_images']
        
        return ConversationHandler.END
    
    async def show_my_ads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إعلانات المستخدم"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        ads = self.db.get_user_ads(user.id)
        
        if not ads:
            await query.edit_message_text(
                "<b>📭 لا توجد إعلانات</b>\n\nلم تنشر أي إعلانات بعد.",
                reply_markup=self.keyboards.create_ad_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        ads_text = "<b>📋 إعلاناتك</b>\n\n"
        
        for ad in ads[:5]:
            status_icon = "✅" if ad['status'] == 'approved' else "⏳" if ad['status'] == 'pending' else "❌"
            price = ad['final_price'] or ad['price']
            
            ads_text += f"""
{status_icon} <b>{ad['title']}</b>
💰 <b>السعر:</b> {price} {CURRENCY_SYMBOL}
📊 <b>الحالة:</b> {ad['status']}
📅 <b>التاريخ:</b> {ad['created_at'][:16]}
━━━━━━━━━━━━━━━━━━━━
"""
        
        await query.edit_message_text(
            ads_text,
            reply_markup=self.keyboards.create_ad_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    # ==================== 🔗 دوال روابط النقاط ====================
    async def show_point_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض روابط النقاط"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "<b>🔗 روابط النقاط المؤقتة</b>\n\n"
            "يمكنك استخدام روابط النقاط المؤقتة\n"
            "للحصول على نقاط مجانية.\n\n"
            "<b>كيفية الاستخدام:</b>\n"
            "1. اضغط على 'روابط متاحة'\n"
            "2. اختر رابط النقاط\n"
            "3. اضغط على الرابط لتحصل على النقاط",
            reply_markup=self.keyboards.point_links_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    async def show_available_point_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض روابط النقاط المتاحة"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        point_links = self.db.get_active_point_links()
        
        if not point_links:
            await query.edit_message_text(
                "<b>🔗 لا توجد روابط نقاط متاحة حالياً</b>\n\n"
                "يمكنك الحصول على نقاط من:\n"
                f"1. التواصل مع {ADMIN_CONTACT}\n"
                f"2. القناة: {CHANNEL_POINTS_LINK}",
                reply_markup=self.keyboards.point_links_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        links_text = "<b>🔗 روابط النقاط المتاحة</b>\n\n"
        
        keyboard = []
        
        for link in point_links[:10]:
            expiry_time = datetime.strptime(link['expiry_time'], "%Y-%m-%d %H:%M:%S")
            time_left = expiry_time - datetime.now()
            hours_left = max(0, int(time_left.total_seconds() // 3600))
            
            links_text += f"""
💰 <b>النقاط:</b> {link['points_per_user']} {CURRENCY_SYMBOL}
👥 <b>المتبقي:</b> {link['max_users'] - link['used_count']}/{link['max_users']}
⏰ <b>الوقت المتبقي:</b> {hours_left} ساعة
━━━━━━━━━━━━━━━━━━━━
"""
            
            link_url = f"https://t.me/{(await context.bot.get_me()).username}?start={link['link_code']}"
            keyboard.append([
                InlineKeyboardButton(
                    f"🔗 رابط {link['points_per_user']} {CURRENCY_SYMBOL}",
                    url=link_url
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data="point_links"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        await query.edit_message_text(
            links_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # ==================== 👑 دوال الأدمن ====================
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة تحكم الأدمن"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        stats = self.db.get_stats()
        
        admin_text = f"""
<b>👑 لوحة التحكم الإدارية ⚡</b>

<b>📊 إحصائيات البوت:</b>
👥 <b>المستخدمون:</b> {stats['total_users']} ({stats['active_users']} نشط)
🛒 <b>المنتجات:</b> {stats['total_products']}
📦 <b>الطلبات:</b> {stats['total_orders']}
⏳ <b>طلبات معلقة:</b> {stats['pending_orders']}
👑 <b>تحتاج متابعة:</b> {stats['pending_admin_orders']}
💰 <b>نقاط مضافة:</b> {stats['total_points_added']} {CURRENCY_SYMBOL}
📢 <b>إعلانات معلقة:</b> {stats['pending_ads']}
🔗 <b>روابط نقاط نشطة:</b> {stats['active_point_links']}

<b>🎯 اختر الإجراء المطلوب:</b> 👇
"""
        
        await query.edit_message_text(
            admin_text,
            reply_markup=self.keyboards.admin_panel(),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_admin_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إجراءات الأدمن"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        if data == "admin_manage_products":
            await self.show_admin_manage_products(update, context)
        elif data == "admin_pending_orders":
            await self.show_admin_pending_orders(update, context)
        elif data == "admin_all_orders":
            await self.show_admin_all_orders(update, context)
        elif data == "admin_point_requests":
            await self.show_admin_point_requests(update, context)
        elif data == "admin_stats":
            await self.show_admin_stats(update, context)
        elif data == "admin_add_product":
            await self.start_admin_add_product(update, context)
        elif data == "admin_user_ads":
            await self.show_admin_user_ads(update, context)
        elif data == "admin_point_links":
            await self.show_admin_point_links(update, context)
        elif data == "admin_manage_users":
            await self.show_admin_manage_users(update, context)
        elif data == "admin_broadcast":
            await self.start_admin_broadcast(update, context)
        elif data == "admin_settings":
            await self.show_admin_settings(update, context)
        elif data == "admin_add_points":
            await self.start_admin_add_points(update, context)
        elif data.startswith("admin_ad_"):
            await self.handle_admin_ad_actions(update, context)
        elif data.startswith("admin_product_"):
            product_id = int(data.split("_")[2])
            await self.show_admin_product_detail(update, context, product_id)
        elif data.startswith("admin_order_"):
            order_id = int(data.split("_")[2])
            await self.show_admin_order_detail(update, context, order_id)
        elif data.startswith("admin_point_req_"):
            request_id = int(data.split("_")[3])
            await self.show_admin_point_request_detail(update, context, request_id)
        elif data == "admin_create_point_link":
            await self.start_create_point_link(update, context)
        elif data == "admin_list_point_links":
            await self.show_admin_list_point_links(update, context)
        else:
            await query.answer("⏳ هذه الميزة قيد التطوير!", show_alert=True)
    
    async def handle_admin_ad_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إجراءات الأدمن على الإعلانات"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("admin_ad_approve_"):
            ad_id = int(data.split("_")[3])
            await self.approve_ad(update, context, ad_id)
        elif data.startswith("admin_ad_reject_"):
            ad_id = int(data.split("_")[3])
            await self.reject_ad(update, context, ad_id)
        elif data.startswith("admin_ad_to_product_"):
            ad_id = int(data.split("_")[4])
            await self.convert_ad_to_product(update, context, ad_id)
        else:
            await query.answer("⏳ هذه الميزة قيد التطوير!", show_alert=True)
    
    async def show_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات الأدمن"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        stats = self.db.get_stats()
        
        stats_text = f"""
<b>📊 الإحصائيات الكاملة</b>

<b>👥 المستخدمون:</b>
• إجمالي المستخدمين: {stats['total_users']}
• المستخدمون النشطون اليوم: {stats['today_users']}
• المستخدمون النشطون (24 ساعة): {stats['active_users']}

<b>🛒 المنتجات:</b>
• إجمالي المنتجات: {stats['total_products']}
• إجمالي المبيعات: {stats['total_sales']}

<b>📦 الطلبات:</b>
• إجمالي الطلبات: {stats['total_orders']}
• الطلبات المعلقة: {stats['pending_orders']}
• تحتاج متابعة أدمن: {stats['pending_admin_orders']}
• إجمالي الإيرادات: {stats['total_revenue']} {CURRENCY_SYMBOL}

<b>💰 النقاط:</b>
• إجمالي النقاط المضافة: {stats['total_points_added']} {CURRENCY_SYMBOL}
• طلبات نقاط معلقة: {stats['pending_point_requests']}

<b>👥 الإحالات:</b>
• إجمالي الإحالات: {stats['total_referrals']}
• نقاط الإحالات: {stats['referral_points']} {CURRENCY_SYMBOL}

<b>📢 الإعلانات:</b>
• إجمالي الإعلانات: {stats['total_ads']}
• إعلانات معلقة: {stats['pending_ads']}

<b>🔗 روابط النقاط:</b>
• إجمالي الروابط: {stats['total_point_links']}
• روابط نشطة: {stats['active_point_links']}
"""
        
        await query.edit_message_text(
            stats_text,
            reply_markup=self.keyboards.admin_panel(),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_manage_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إدارة المنتجات للأدمن"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        products = self.db.get_products(active_only=False)
        
        if not products:
            await query.edit_message_text(
                "<b>🛒 لا توجد منتجات</b>\n\nلم يتم إضافة أي منتجات بعد.",
                reply_markup=self.keyboards.admin_panel(),
                parse_mode=ParseMode.HTML
            )
            return
        
        products_text = "<b>🛒 إدارة المنتجات</b>\n\n"
        
        keyboard = []
        for product in products[:10]:
            status = "✅" if product['is_active'] == 1 else "❌"
            featured = "⭐" if product['is_featured'] == 1 else ""
            admin_req = "👑" if product['requires_admin'] == 1 else ""
            stock = "∞" if product['stock'] == -1 else product['stock']
            
            button_text = f"{status} {featured}{admin_req} {product['name']} - {CURRENCY_SYMBOL}{product['price']}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"admin_product_{product['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_product"),
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
        ])
        
        await query.edit_message_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_product_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        """عرض تفاصيل المنتج للإدارة"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        product = self.db.get_product(product_id)
        
        if not product:
            await query.edit_message_text("❌ المنتج غير موجود")
            return
        
        product_text = f"""
<b>🛒 تفاصيل المنتج #{product['id']}</b>

<b>📌 الاسم:</b> {product['name']}
<b>💰 السعر:</b> {product['price']} {CURRENCY_SYMBOL}
<b>📦 المخزون:</b> {'∞' if product['stock'] == -1 else product['stock']}
<b>📝 الوصف:</b> {product['description']}
<b>🏷️ الفئة:</b> {product['category_name']}
<b>✨ مميز:</b> {'✅' if product['is_featured'] == 1 else '❌'}
<b>👑 يتطلب أدمن:</b> {'✅' if product['requires_admin'] == 1 else '❌'}
<b>📤 نوع التسليم:</b> {product['delivery_type']}
<b>✅ النشاط:</b> {'✅' if product['is_active'] == 1 else '❌'}
"""
        
        await query.edit_message_text(
            product_text,
            reply_markup=self.keyboards.admin_product_actions(product_id),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_pending_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الطلبات المعلقة للأدمن"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        orders = self.db.get_pending_orders()
        
        if not orders:
            await query.edit_message_text(
                "<b>📦 لا توجد طلبات معلقة</b>\n\nكل الطلبات تمت معالجتها!",
                reply_markup=self.keyboards.admin_panel(),
                parse_mode=ParseMode.HTML
            )
            return
        
        orders_text = "<b>📦 الطلبات المعلقة</b>\n\n"
        
        keyboard = []
        for order in orders[:10]:
            admin_req = "👑" if order['requires_admin_action'] == 1 else ""
            orders_text += f"{admin_req} طلب #{order['id']} - {order['product_name']} - {order['customer_name']}\n"
            keyboard.append([
                InlineKeyboardButton(f"{admin_req} طلب #{order['id']}", callback_data=f"admin_order_{order['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        await query.edit_message_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_all_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض جميع الطلبات"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT o.*, p.name as product_name, u.username as customer_name, u.first_name
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            JOIN users u ON o.user_id = u.user_id 
            ORDER BY o.created_at DESC 
            LIMIT 20
        ''')
        rows = cursor.fetchall()
        
        if not rows:
            await query.edit_message_text(
                "<b>📦 لا توجد طلبات</b>",
                reply_markup=self.keyboards.admin_panel(),
                parse_mode=ParseMode.HTML
            )
            return
        
        orders_text = "<b>📦 جميع الطلبات (آخر 20)</b>\n\n"
        
        for row in rows:
            order_id, order_code, user_id, product_id, quantity, total_points, status, admin_notes, delivery_data, requires_admin, admin_assigned, created_at, completed_at, product_name, customer_name, first_name = row
            
            status_icon = "✅" if status == 'completed' else "⏳" if status == 'pending' else "❌"
            admin_req = "👑" if requires_admin == 1 else ""
            
            orders_text += f"{status_icon}{admin_req} طلب #{order_id} - {product_name} - {first_name} - {CURRENCY_SYMBOL}{total_points}\n"
        
        await query.edit_message_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
                 InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
            ]),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_order_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
        """عرض تفاصيل الطلب للأدمن"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        order = self.db.get_order_by_id(order_id)
        
        if not order:
            await query.edit_message_text("❌ الطلب غير موجود")
            return
        
        order_text = f"""
<b>📦 تفاصيل الطلب #{order['id']}</b>

<b>🆔 كود الطلب:</b> <code>{order['order_code']}</code>
<b>👤 العميل:</b> {order['first_name']} (@{order['customer_name']})
<b>🆔 ID العميل:</b> <code>{order['user_id']}</code>
<b>🛒 المنتج:</b> {order['product_name']}
<b>💰 المبلغ:</b> {order['total_points']} {CURRENCY_SYMBOL}
<b>📅 التاريخ:</b> {order['created_at'][:16]}
<b>📊 الحالة:</b> {order['status']}
<b>👑 يحتاج متابعة:</b> {'✅' if order['requires_admin_action'] == 1 else '❌'}
"""
        
        if order['admin_notes']:
            order_text += f"\n<b>📝 ملاحظات الأدمن:</b>\n{order['admin_notes']}"
        
        if order['delivery_data']:
            order_text += f"\n<b>📦 بيانات التسليم:</b>\n{order['delivery_data']}"
        
        await query.edit_message_text(
            order_text,
            reply_markup=self.keyboards.admin_order_actions(order_id),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_point_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض طلبات شحن النقاط المعلقة"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        requests = self.db.get_pending_point_requests()
        
        if not requests:
            await query.edit_message_text(
                "<b>💰 لا توجد طلبات شحن نقاط معلقة</b>",
                reply_markup=self.keyboards.admin_panel(),
                parse_mode=ParseMode.HTML
            )
            return
        
        requests_text = "<b>💰 طلبات شحن النقاط المعلقة</b>\n\n"
        
        keyboard = []
        for req in requests[:10]:
            requests_text += f"طلب #{req['id']} - {req['first_name']} - {req['amount']} {CURRENCY_SYMBOL}\n"
            keyboard.append([
                InlineKeyboardButton(f"طلب #{req['id']}", callback_data=f"admin_point_req_{req['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        await query.edit_message_text(
            requests_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_point_request_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: int):
        """عرض تفاصيل طلب شحن النقاط"""
        query = update.callback_query
        await query.answer()
        
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT pr.*, u.username, u.first_name 
            FROM point_requests pr 
            JOIN users u ON pr.user_id = u.user_id 
            WHERE pr.id = ?
        ''', (request_id,))
        row = cursor.fetchone()
        
        if not row:
            await query.edit_message_text("❌ طلب النقاط غير موجود")
            return
        
        columns = [description[0] for description in cursor.description]
        request = dict(zip(columns, row))
        
        request_text = f"""
<b>💰 تفاصيل طلب النقاط #{request['id']}</b>

<b>👤 المستخدم:</b> {request['first_name']} (@{request['username']})
<b>🆔 ID المستخدم:</b> <code>{request['user_id']}</code>
<b>💰 المبلغ:</b> {request['amount']} {CURRENCY_SYMBOL}
<b>📅 التاريخ:</b> {request['created_at'][:16]}
<b>📊 الحالة:</b> {request['status']}
"""
        
        if request['proof_text']:
            request_text += f"\n<b>📋 نص الإثبات:</b>\n{request['proof_text']}"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ قبول الطلب", callback_data=f"admin_approve_point_req_{request_id}"),
                InlineKeyboardButton("❌ رفض الطلب", callback_data=f"admin_reject_point_req_{request_id}")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_point_requests"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
            ]
        ])
        
        await query.edit_message_text(
            request_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def start_admin_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إضافة منتج جديد"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        context.user_data['add_product_step'] = 1
        
        await query.edit_message_text(
            "<b>➕ إضافة منتج جديد - الخطوة 1</b>\n\n<b>أرسل اسم المنتج:</b>",
            parse_mode=ParseMode.HTML
        )
        return ADD_PRODUCT_NAME
    
    async def process_admin_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة منتج جديد"""
        user = update.effective_user
        message_text = update.message.text
        
        if context.user_data.get('add_product_step') == 1:
            context.user_data['product_name'] = message_text
            context.user_data['add_product_step'] = 2
            
            await update.message.reply_text(
                f"<b>➕ إضافة منتج جديد - الخطوة 2</b>\n\n"
                f"<b>الاسم:</b> {message_text}\n\n"
                f"<b>أرسل وصف المنتج:</b>",
                parse_mode=ParseMode.HTML
            )
            return ADD_PRODUCT_DESC
        
        elif context.user_data.get('add_product_step') == 2:
            context.user_data['product_desc'] = message_text
            context.user_data['add_product_step'] = 3
            
            await update.message.reply_text(
                f"<b>➕ إضافة منتج جديد - الخطوة 3</b>\n\n"
                f"<b>الاسم:</b> {context.user_data['product_name']}\n"
                f"<b>الوصف:</b> {message_text[:50]}...\n\n"
                f"<b>أرسل سعر المنتج (بالنقاط):</b>",
                parse_mode=ParseMode.HTML
            )
            return ADD_PRODUCT_PRICE
        
        elif context.user_data.get('add_product_step') == 3:
            try:
                price = int(message_text)
                if price <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال سعر صحيح أكبر من صفر")
                    return ADD_PRODUCT_PRICE
                
                context.user_data['product_price'] = price
                context.user_data['add_product_step'] = 4
                
                await update.message.reply_text(
                    f"<b>➕ إضافة منتج جديد - الخطوة 4</b>\n\n"
                    f"<b>الاسم:</b> {context.user_data['product_name']}\n"
                    f"<b>السعر:</b> {price} {CURRENCY_SYMBOL}\n\n"
                    f"<b>أرسل المخزون (-1 لغير محدود):</b>",
                    parse_mode=ParseMode.HTML
                )
                return ADD_PRODUCT_STOCK
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال سعر صحيح (أرقام فقط)")
                return ADD_PRODUCT_PRICE
        
        elif context.user_data.get('add_product_step') == 4:
            try:
                stock = int(message_text)
                context.user_data['product_stock'] = stock
                context.user_data['add_product_step'] = 5
                
                await update.message.reply_text(
                    f"<b>➕ إضافة منتج جديد - الخطوة 5</b>\n\n"
                    f"<b>الاسم:</b> {context.user_data['product_name']}\n"
                    f"<b>السعر:</b> {context.user_data['product_price']} {CURRENCY_SYMBOL}\n"
                    f"<b>المخزون:</b> {'∞' if stock == -1 else stock}\n\n"
                    f"<b>اختر الفئة:</b>",
                    reply_markup=self.keyboards.categories_for_admin("add_product"),
                    parse_mode=ParseMode.HTML
                )
                return ADD_PRODUCT_CATEGORY
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال مخزون صحيح (أرقام فقط)")
                return ADD_PRODUCT_STOCK
    
    async def complete_admin_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: int):
        """إكمال إضافة المنتج"""
        user = update.effective_user
        
        name = context.user_data.get('product_name')
        desc = context.user_data.get('product_desc')
        price = context.user_data.get('product_price')
        stock = context.user_data.get('product_stock', -1)
        
        product_id = self.db.add_product(
            category_id=category_id,
            name=name,
            description=desc,
            price=price,
            stock=stock,
            requires_admin=0,
            is_featured=0
        )
        
        success_text = f"""
<b>✅ تمت إضافة المنتج بنجاح!</b>

<b>🆔 رقم المنتج:</b> #{product_id}
<b>📌 الاسم:</b> {name}
<b>💰 السعر:</b> {price} {CURRENCY_SYMBOL}
<b>📦 المخزون:</b> {'∞' if stock == -1 else stock}
<b>📝 الوصف:</b> {desc[:100]}...
"""
        
        await update.message.reply_text(
            success_text,
            reply_markup=self.keyboards.admin_panel(),
            parse_mode=ParseMode.HTML
        )
        
        del context.user_data['add_product_step']
        del context.user_data['product_name']
        del context.user_data['product_desc']
        del context.user_data['product_price']
        del context.user_data['product_stock']
        
        return ConversationHandler.END
    
    async def show_admin_user_ads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إعلانات المستخدمين للأدمن"""
        query = update.callback_query
        await query.answer()
        
        pending_ads = self.db.get_pending_ads()
        
        if not pending_ads:
            await query.edit_message_text(
                "<b>📢 لا توجد إعلانات معلقة</b>\n\nكل الإعلانات تمت مراجعتها!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
                ]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        ads_text = "<b>📢 الإعلانات المعلقة</b>\n\n"
        
        for ad in pending_ads[:5]:
            ads_text += f"""
<b>🆔 #{ad['id']}</b>
👤 <b>الناشر:</b> {ad['first_name']} (@{ad['username']})
📌 <b>العنوان:</b> {ad['title']}
💰 <b>السعر:</b> {ad['price']} {CURRENCY_SYMBOL}
📅 <b>التاريخ:</b> {ad['created_at'][:16]}
━━━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = []
        for ad in pending_ads[:3]:
            keyboard.append([
                InlineKeyboardButton(f"📋 مراجعة #{ad['id']}", callback_data=f"admin_ad_review_{ad['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
        ])
        
        await query.edit_message_text(
            ads_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_ad_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ad_id: int):
        """عرض تفاصيل الإعلان للأدمن"""
        query = update.callback_query
        await query.answer()
        
        ad = self.db.get_ad(ad_id)
        
        if not ad:
            await query.edit_message_text("❌ الإعلان غير موجود")
            return
        
        images = json.loads(ad['images']) if ad['images'] else []
        
        ad_text = f"""
<b>📢 تفاصيل الإعلان #{ad['id']}</b>

<b>👤 الناشر:</b> {ad['first_name']} (@{ad['username']})
<b>🆔 ID الناشر:</b> <code>{ad['user_id']}</code>
<b>📌 العنوان:</b> {ad['title']}
<b>💰 السعر المقترح:</b> {ad['price']} {CURRENCY_SYMBOL}
<b>📊 الحالة:</b> {ad['status']}
<b>📸 الصور:</b> {len(images)} صورة/فيديو
<b>📅 التاريخ:</b> {ad['created_at'][:16]}

<b>📝 الوصف:</b>
{ad['description']}
"""
        
        if ad['admin_notes']:
            ad_text += f"\n<b>📋 ملاحظات الأدمن:</b>\n{ad['admin_notes']}"
        
        if ad['final_price']:
            ad_text += f"\n<b>💰 السعر النهائي:</b> {ad['final_price']} {CURRENCY_SYMBOL}"
        
        await query.edit_message_text(
            ad_text,
            reply_markup=self.keyboards.admin_user_ads_actions(ad_id),
            parse_mode=ParseMode.HTML
        )
    
    async def approve_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ad_id: int):
        """قبول الإعلان"""
        query = update.callback_query
        await query.answer()
        
        ad = self.db.get_ad(ad_id)
        
        if not ad:
            await query.edit_message_text("❌ الإعلان غير موجود")
            return
        
        context.user_data['approve_ad_id'] = ad_id
        
        await query.edit_message_text(
            f"<b>✅ قبول الإعلان #{ad_id}</b>\n\n"
            f"<b>العنوان:</b> {ad['title']}\n"
            f"<b>السعر المقترح:</b> {ad['price']} {CURRENCY_SYMBOL}\n\n"
            f"<b>أرسل السعر النهائي (يمكنك استخدام نفس السعر أو تعديله):</b>",
            parse_mode=ParseMode.HTML
        )
    
    async def reject_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ad_id: int):
        """رفض الإعلان"""
        query = update.callback_query
        await query.answer()
        
        ad = self.db.get_ad(ad_id)
        
        if not ad:
            await query.edit_message_text("❌ الإعلان غير موجود")
            return
        
        context.user_data['reject_ad_id'] = ad_id
        
        await query.edit_message_text(
            f"<b>❌ رفض الإعلان #{ad_id}</b>\n\n"
            f"<b>العنوان:</b> {ad['title']}\n\n"
            f"<b>أرسل سبب الرفض:</b>",
            parse_mode=ParseMode.HTML
        )
    
    async def convert_ad_to_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ad_id: int):
        """تحويل الإعلان إلى منتج"""
        query = update.callback_query
        await query.answer()
        
        ad = self.db.get_ad(ad_id)
        
        if not ad:
            await query.edit_message_text("❌ الإعلان غير موجود")
            return
        
        context.user_data['convert_ad_id'] = ad_id
        
        await query.edit_message_text(
            f"<b>🛒 تحويل الإعلان إلى منتج</b>\n\n"
            f"<b>الإعلان:</b> #{ad_id} - {ad['title']}\n"
            f"<b>السعر النهائي:</b> {ad['final_price'] or ad['price']} {CURRENCY_SYMBOL}\n\n"
            f"<b>اختر الفئة المناسبة:</b>",
            reply_markup=self.keyboards.categories_for_admin("add_product"),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_point_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إدارة روابط النقاط"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "<b>🔗 إدارة روابط النقاط المؤقتة</b>\n\n"
            "يمكنك إنشاء روابط نقاط مؤقتة\n"
            "للمستخدمين للحصول على نقاط مجانية.\n\n"
            "<b>مثال:</b>\n"
            "• 1.5 نقطة لكل مستخدم\n"
            "• 30 مستخدم كحد أقصى\n"
            "• صالح لمدة ساعة واحدة",
            reply_markup=self.keyboards.admin_point_links_actions(),
            parse_mode=ParseMode.HTML
        )
    
    async def start_create_point_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إنشاء رابط نقاط مؤقت"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        context.user_data['create_point_link_step'] = 1
        
        await query.edit_message_text(
            "<b>🔗 إنشاء رابط نقاط مؤقت - الخطوة 1</b>\n\n"
            "<b>أرسل عدد النقاط لكل مستخدم:</b>\n"
            "<i>يمكن أن يكون كسراً مثل 1.5</i>",
            parse_mode=ParseMode.HTML
        )
        return ADD_POINTS_LINK_POINTS
    
    async def process_create_point_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إنشاء رابط نقاط"""
        user = update.effective_user
        message_text = update.message.text
        
        if context.user_data.get('create_point_link_step') == 1:
            try:
                points = float(message_text)
                if points <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال عدد نقاط صحيح أكبر من صفر")
                    return ADD_POINTS_LINK_POINTS
                
                context.user_data['points_per_user'] = points
                context.user_data['create_point_link_step'] = 2
                
                await update.message.reply_text(
                    f"<b>🔗 إنشاء رابط نقاط مؤقت - الخطوة 2</b>\n\n"
                    f"<b>النقاط لكل مستخدم:</b> {points} {CURRENCY_SYMBOL}\n\n"
                    f"<b>أرسل الحد الأقصى للمستخدمين:</b>",
                    parse_mode=ParseMode.HTML
                )
                return ADD_POINTS_LINK_USERS
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال عدد نقاط صحيح")
                return ADD_POINTS_LINK_POINTS
        
        elif context.user_data.get('create_point_link_step') == 2:
            try:
                max_users = int(message_text)
                if max_users <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال عدد مستخدمين صحيح أكبر من صفر")
                    return ADD_POINTS_LINK_USERS
                
                context.user_data['max_users'] = max_users
                context.user_data['create_point_link_step'] = 3
                
                await update.message.reply_text(
                    f"<b>🔗 إنشاء رابط نقاط مؤقت - الخطوة 3</b>\n\n"
                    f"<b>النقاط لكل مستخدم:</b> {context.user_data['points_per_user']} {CURRENCY_SYMBOL}\n"
                    f"<b>الحد الأقصى للمستخدمين:</b> {max_users}\n\n"
                    f"<b>أرسل عدد الساعات الصالحة:</b>",
                    parse_mode=ParseMode.HTML
                )
                return ADD_POINTS_LINK_HOURS
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال عدد مستخدمين صحيح")
                return ADD_POINTS_LINK_USERS
        
        elif context.user_data.get('create_point_link_step') == 3:
            try:
                hours = int(message_text)
                if hours <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال عدد ساعات صحيح أكبر من صفر")
                    return ADD_POINTS_LINK_HOURS
                
                points_per_user = context.user_data['points_per_user']
                max_users = context.user_data['max_users']
                
                # عرض تأكيد إنشاء الرابط مع الزر المؤكد
                await update.message.reply_text(
                    f"<b>🔗 تأكيد إنشاء رابط النقاط</b>\n\n"
                    f"<b>💰 النقاط لكل مستخدم:</b> {points_per_user} {CURRENCY_SYMBOL}\n"
                    f"<b>👥 الحد الأقصى للمستخدمين:</b> {max_users}\n"
                    f"<b>⏰ مدة الصلاحية:</b> {hours} ساعة\n\n"
                    f"<b>هل تريد إنشاء الرابط بهذه المواصفات؟</b>",
                    reply_markup=self.keyboards.confirm_create_point_link(points_per_user, max_users, hours),
                    parse_mode=ParseMode.HTML
                )
                
                del context.user_data['create_point_link_step']
                del context.user_data['points_per_user']
                del context.user_data['max_users']
                
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال عدد ساعات صحيح")
                return ADD_POINTS_LINK_HOURS
    
    async def show_admin_list_point_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض روابط النقاط النشطة"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        point_links = self.db.get_active_point_links()
        
        if not point_links:
            await query.edit_message_text(
                "<b>🔗 لا توجد روابط نقاط نشطة</b>",
                reply_markup=self.keyboards.admin_point_links_actions(),
                parse_mode=ParseMode.HTML
            )
            return
        
        links_text = "<b>🔗 روابط النقاط النشطة</b>\n\n"
        
        for link in point_links[:5]:
            expiry_time = datetime.strptime(link['expiry_time'], "%Y-%m-%d %H:%M:%S")
            time_left = expiry_time - datetime.now()
            hours_left = max(0, int(time_left.total_seconds() // 3600))
            
            links_text += f"""
<b>🆔 #{link['id']}</b>
💰 <b>النقاط:</b> {link['points_per_user']} {CURRENCY_SYMBOL}
👥 <b>المستخدمون:</b> {link['used_count']}/{link['max_users']}
⏰ <b>المتبقي:</b> {hours_left} ساعة
<b>🔗 الرابط:</b> <code>https://t.me/{(await context.bot.get_me()).username}?start={link['link_code']}</code>
━━━━━━━━━━━━━━━━━━━━
"""
        
        await query.edit_message_text(
            links_text,
            reply_markup=self.keyboards.admin_point_links_actions(),
            parse_mode=ParseMode.HTML
        )
    
    async def show_admin_manage_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إدارة المستخدمين"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, points, is_admin, is_blocked FROM users ORDER BY user_id DESC LIMIT 20')
        rows = cursor.fetchall()
        
        if not rows:
            await query.edit_message_text(
                "<b>👥 لا يوجد مستخدمين بعد</b>",
                reply_markup=self.keyboards.admin_panel(),
                parse_mode=ParseMode.HTML
            )
            return
        
        users_text = "<b>👥 إدارة المستخدمين (آخر 20)</b>\n\n"
        
        for row in rows:
            user_id, username, first_name, points, is_admin, is_blocked = row
            admin_icon = "👑" if is_admin else ""
            blocked_icon = "⛔" if is_blocked else ""
            users_text += f"{admin_icon}{blocked_icon} <b>{first_name}</b> (@{username or 'لا يوجد'}) - ID: <code>{user_id}</code> - النقاط: {points}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
        ])
        
        await query.edit_message_text(
            users_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def start_admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إرسال إشعار لجميع المستخدمين"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        context.user_data['broadcasting'] = True
        await query.edit_message_text(
            "<b>📢 إرسال إشعار لجميع المستخدمين</b>\n\nأرسل النص الذي تريد إرساله:",
            parse_mode=ParseMode.HTML
        )
        return BROADCAST_MESSAGE
    
    async def process_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة البث"""
        user = update.effective_user
        message_text = update.message.text
        
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        
        success_count = 0
        fail_count = 0
        
        for user_row in users:
            user_id = user_row[0]
            try:
                await context.bot.send_message(
                    user_id,
                    f"<b>📢 إشعار من الإدارة:</b>\n\n{message_text}",
                    parse_mode=ParseMode.HTML
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"فشل إرسال إشعار إلى {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ تم إرسال الإشعار إلى {success_count} مستخدم\n❌ فشل إرسال إلى {fail_count} مستخدم",
            reply_markup=self.keyboards.admin_panel()
        )
        
        del context.user_data['broadcasting']
        return ConversationHandler.END
    
    async def show_admin_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إعدادات البوت للأدمن"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        settings_text = f"""
<b>⚙️ إعدادات البوت الإدارية</b>

<b>🔧 الإعدادات الحالية:</b>
🔹 <b>رمز العملة:</b> {CURRENCY_SYMBOL}
🔹 <b>نقاط الإحالة:</b> {REFERRAL_POINTS}
🔹 <b>معرف الأدمن:</b> {ADMIN_ID}
🔹 <b>تواصل الأدمن:</b> {ADMIN_CONTACT}
🔹 <b>القناة الإجبارية:</b> {REQUIRED_CHANNEL}

<b>📊 قاعدة البيانات:</b>
• متجر كامل متكامل
• دعم متعدد الفئات
• نظام طلبات متقدم
• تقارير وإحصائيات

<b>🎯 الميزات المفعلة:</b>
✅ متجر منتجات رقمية
✅ نظام نقاط داخلي
✅ تحويل النقاط بين المستخدمين
✅ نشر إعلانات المستخدمين
✅ روابط نقاط مؤقتة
✅ نظام إحالات
✅ لوحة تحكم متكاملة
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث الإعدادات", callback_data="admin_refresh_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
        ])
        
        await query.edit_message_text(
            settings_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def start_admin_add_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إضافة نقاط لمستخدم"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        
        context.user_data['add_points_step'] = 1
        
        await query.edit_message_text(
            "<b>🎁 إضافة نقاط لمستخدم - الخطوة 1</b>\n\n"
            "<b>أرسل معرف المستخدم (User ID):</b>",
            parse_mode=ParseMode.HTML
        )
        return ADD_POINTS_TO_USER
    
    async def process_admin_add_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة نقاط"""
        user = update.effective_user
        message_text = update.message.text
        
        if context.user_data.get('add_points_step') == 1:
            try:
                to_user_id = int(message_text)
                to_user = self.db.get_user(to_user_id)
                
                if not to_user:
                    await update.message.reply_text("❌ المستخدم غير موجود")
                    return ADD_POINTS_TO_USER
                
                context.user_data['add_points_user'] = to_user_id
                context.user_data['add_points_step'] = 2
                
                await update.message.reply_text(
                    f"<b>🎁 إضافة نقاط لمستخدم - الخطوة 2</b>\n\n"
                    f"👤 <b>المستخدم:</b> {to_user['first_name']} (@{to_user['username'] or 'لا يوجد'})\n"
                    f"💰 <b>رصيده الحالي:</b> {to_user['points']} {CURRENCY_SYMBOL}\n\n"
                    f"<b>أرسل عدد النقاط المطلوب إضافتها:</b>",
                    parse_mode=ParseMode.HTML
                )
                return ADD_POINTS_AMOUNT
                
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال معرف مستخدم صحيح")
                return ADD_POINTS_TO_USER
        
        elif context.user_data.get('add_points_step') == 2:
            try:
                amount = int(message_text)
                
                if amount <= 0:
                    await update.message.reply_text("❌ الرجاء إرسال عدد نقاط صحيح أكبر من صفر")
                    return ADD_POINTS_AMOUNT
                
                to_user_id = context.user_data.get('add_points_user')
                self.db.update_user_points(to_user_id, amount, "add")
                
                to_user = self.db.get_user(to_user_id)
                
                await update.message.reply_text(
                    f"✅ <b>تمت إضافة النقاط بنجاح!</b>\n\n"
                    f"👤 <b>المستخدم:</b> {to_user['first_name']}\n"
                    f"💰 <b>المبلغ المضاف:</b> {amount} {CURRENCY_SYMBOL}\n"
                    f"💳 <b>رصيده الجديد:</b> {to_user['points']} {CURRENCY_SYMBOL}",
                    reply_markup=self.keyboards.admin_panel(),
                    parse_mode=ParseMode.HTML
                )
                
                del context.user_data['add_points_step']
                del context.user_data['add_points_user']
                return ConversationHandler.END
                
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال عدد نقاط صحيح")
                return ADD_POINTS_AMOUNT
    
    # ==================== 📝 معالجة الرسائل النصية ====================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية"""
        user = update.effective_user
        message_text = update.message.text
        
        self.db.update_last_active(user.id)
        
        # البحث
        if context.user_data.get('searching'):
            await self.process_search(update, context)
            return
        
        # إذا كان المستخدم في عملية إنشاء إعلان
        if context.user_data.get('create_ad_step'):
            if context.user_data['create_ad_step'] in [1, 2, 3]:
                await self.process_create_ad(update, context)
            else:
                await update.message.reply_text(
                    "📸 الرجاء إرسال صورة للمنتج أو اضغط على /skip",
                    reply_markup=self.keyboards.main_menu(user.id)
                )
            return
        
        # إذا كان المستخدم في عملية تحويل نقاط
        if context.user_data.get('transfer_step'):
            await self.process_transfer_points(update, context)
            return
        
        # إذا كان الأدمن في عملية إضافة منتج
        if context.user_data.get('add_product_step'):
            await self.process_admin_add_product(update, context)
            return
        
        # إذا كان الأدمن في عملية إنشاء رابط نقاط
        if context.user_data.get('create_point_link_step'):
            await self.process_create_point_link(update, context)
            return
        
        # إذا كان الأدمن في عملية قبول إعلان
        if 'approve_ad_id' in context.user_data:
            ad_id = context.user_data['approve_ad_id']
            try:
                final_price = float(message_text)
                self.db.update_ad_status(ad_id, 'approved', final_price=final_price)
                await update.message.reply_text(
                    f"✅ تم قبول الإعلان #{ad_id} بنجاح!",
                    reply_markup=self.keyboards.admin_panel()
                )
                del context.user_data['approve_ad_id']
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال سعر صحيح")
            return
        
        # إذا كان الأدمن في عملية رفض إعلان
        if 'reject_ad_id' in context.user_data:
            ad_id = context.user_data['reject_ad_id']
            reason = message_text
            self.db.update_ad_status(ad_id, 'rejected', admin_notes=reason)
            await update.message.reply_text(
                f"❌ تم رفض الإعلان #{ad_id} بنجاح!",
                reply_markup=self.keyboards.admin_panel()
            )
            del context.user_data['reject_ad_id']
            return
        
        # إذا كان الأدمن في عملية تحويل إعلان لمنتج
        if 'convert_ad_id' in context.user_data:
            try:
                category_id = int(message_text)
                ad_id = context.user_data['convert_ad_id']
                success, message = self.db.approve_ad_to_product(ad_id, category_id)
                
                if success:
                    await update.message.reply_text(
                        f"✅ {message}",
                        reply_markup=self.keyboards.admin_panel()
                    )
                else:
                    await update.message.reply_text(
                        f"❌ {message}",
                        reply_markup=self.keyboards.admin_panel()
                    )
                del context.user_data['convert_ad_id']
            except ValueError:
                await update.message.reply_text("❌ الرجاء إرسال رقم فئة صحيح")
            return
        
        # إذا كان الأدمن في عملية بث
        if context.user_data.get('broadcasting'):
            await self.process_broadcast(update, context)
            return
        
        # إذا كان الأدمن في عملية إضافة نقاط
        if context.user_data.get('add_points_step'):
            await self.process_admin_add_points(update, context)
            return
        
        # إذا كان الأدمن يختار فئة لإضافة منتج
        if context.user_data.get('add_product_step') == 5:
            try:
                category_id = int(message_text)
                await self.complete_admin_add_product(update, context, category_id)
            except:
                await update.message.reply_text("❌ حدث خطأ في اختيار الفئة")
            return
        
        # الرسائل العادية
        await update.message.reply_text(
            "👋 <b>مرحباً بك في البوت!</b>\n\n"
            "🔹 استخدم الأزرار للتنقل\n"
            "🔹 أو استخدم /start للبدء\n"
            "🔹 /store لعرض المتجر",
            reply_markup=self.keyboards.main_menu(user.id),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الصور"""
        user = update.effective_user
        
        if context.user_data.get('create_ad_step') == 4:
            await self.process_ad_image(update, context)
        else:
            await update.message.reply_text(
                "📸 يمكنك استخدام الصور عند نشر إعلان جديد.\nاستخدم /ad للبدء.",
                reply_markup=self.keyboards.main_menu(user.id)
            )
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الفيديوهات"""
        user = update.effective_user
        
        if context.user_data.get('create_ad_step') == 4:
            await self.process_ad_image(update, context)
        else:
            await update.message.reply_text(
                "🎥 يمكنك استخدام الفيديوهات عند نشر إعلان جديد.\nاستخدم /ad للبدء.",
                reply_markup=self.keyboards.main_menu(user.id)
            )
    
    # ==================== 🔧 إعداد المعالجات ====================
    def setup_handlers(self):
        """إعداد معالجات البوت"""
        start_handler = CommandHandler('start', self.start_command)
        store_handler = CommandHandler('store', self.store_command)
        balance_handler = CommandHandler('balance', self.balance_command)
        transfer_handler = CommandHandler('transfer', self.transfer_command)
        ad_handler = CommandHandler('ad', self.create_ad_command)
        myads_handler = CommandHandler('myads', self.my_ads_command)
        id_handler = CommandHandler('id', self.id_command)
        search_handler = CommandHandler('search', self.search_command)
        
        # معالج محادثة تحويل النقاط
        transfer_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_transfer_points, pattern='^start_transfer$')],
            states={
                TRANSFER_POINTS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_transfer_points)],
                TRANSFER_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_transfer_points)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        # معالج محادثة إنشاء إعلان
        create_ad_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_create_ad, pattern='^start_create_ad$')],
            states={
                ADD_AD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_create_ad)],
                ADD_AD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_create_ad)],
                ADD_AD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_create_ad)],
                ADD_AD_IMAGES: [
                    MessageHandler(filters.PHOTO | filters.VIDEO, self.process_ad_image),
                    CommandHandler('skip', self.skip_images),
                    CommandHandler('done', self.done_images)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        # معالج محادثة إضافة منتج جديد (للأدمن)
        admin_add_product_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_admin_add_product, pattern='^admin_add_product$')],
            states={
                ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_admin_add_product)],
                ADD_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_admin_add_product)],
                ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_admin_add_product)],
                ADD_PRODUCT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_admin_add_product)],
                ADD_PRODUCT_CATEGORY: [CallbackQueryHandler(self.handle_category_selection_callback, pattern='^admin_add_cat_')],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        # معالج محادثة إنشاء رابط نقاط (للأدمن)
        create_point_link_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_create_point_link, pattern='^admin_create_point_link$')],
            states={
                ADD_POINTS_LINK_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_create_point_link)],
                ADD_POINTS_LINK_USERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_create_point_link)],
                ADD_POINTS_LINK_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_create_point_link)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        # معالج محادثة البث (للأدمن)
        broadcast_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_admin_broadcast, pattern='^admin_broadcast$')],
            states={
                BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_broadcast)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        # معالج محادثة إضافة نقاط (للأدمن)
        add_points_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_admin_add_points, pattern='^admin_add_points$')],
            states={
                ADD_POINTS_TO_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_admin_add_points)],
                ADD_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_admin_add_points)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        # معالج محادثة البحث
        search_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_search, pattern='^search$')],
            states={
                SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_search)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)],
            allow_reentry=True
        )
        
        callback_handler = CallbackQueryHandler(self.handle_callback)
        message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        photo_handler = MessageHandler(filters.PHOTO, self.handle_photo)
        video_handler = MessageHandler(filters.VIDEO, self.handle_video)
        
        self.application.add_handler(start_handler)
        self.application.add_handler(store_handler)
        self.application.add_handler(balance_handler)
        self.application.add_handler(transfer_handler)
        self.application.add_handler(ad_handler)
        self.application.add_handler(myads_handler)
        self.application.add_handler(id_handler)
        self.application.add_handler(search_handler)
        
        # إضافة معالجات المحادثة
        self.application.add_handler(transfer_conv_handler)
        self.application.add_handler(create_ad_conv_handler)
        self.application.add_handler(admin_add_product_conv_handler)
        self.application.add_handler(create_point_link_conv_handler)
        self.application.add_handler(broadcast_conv_handler)
        self.application.add_handler(add_points_conv_handler)
        self.application.add_handler(search_conv_handler)
        
        # المعالجات العامة
        self.application.add_handler(callback_handler)
        self.application.add_handler(message_handler)
        self.application.add_handler(photo_handler)
        self.application.add_handler(video_handler)
    
    async def handle_category_selection_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة اختيار الفئة من خلال callback"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        category_id = int(data.split("_")[3])
        
        await self.complete_admin_add_product(update, context, category_id)
    
    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء المحادثة"""
        user = update.effective_user
        
        # مسح بيانات المحادثة
        keys_to_delete = [
            'transfer_step', 'transfer_to_user', 'create_ad_step',
            'ad_title', 'ad_desc', 'ad_price', 'ad_images',
            'add_product_step', 'product_name', 'product_desc',
            'product_price', 'product_stock', 'create_point_link_step',
            'points_per_user', 'max_users', 'broadcasting',
            'add_points_step', 'add_points_user', 'approve_ad_id',
            'reject_ad_id', 'convert_ad_id', 'searching'
        ]
        
        for key in keys_to_delete:
            if key in context.user_data:
                del context.user_data[key]
        
        await update.message.reply_text(
            "❌ تم إلغاء العملية.",
            reply_markup=self.keyboards.main_menu(user.id)
        )
        return ConversationHandler.END
    
    def run(self):
        """تشغيل البوت"""
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        logger.info("🤖 البوت يعمل بنجاح...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# ==================== 🚀 تشغيل البوت ====================
if __name__ == "__main__":
    bot = CompleteTelegramShopBot()
    bot.run()
