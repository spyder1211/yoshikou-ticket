from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
import json
import os
import qrcode
import io
import base64
from datetime import datetime, timedelta
import random
import string
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # セッション管理用

# 管理者認証設定
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password123'

def admin_required(f):
    """管理者認証が必要なページのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # セッションまたはクッキーで認証状態を確認
        is_authenticated = (
            session.get('admin_authenticated') or 
            request.cookies.get('admin_authenticated') == 'true'
        )
        
        if not is_authenticated:
            return redirect(url_for('admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

# データファイルのパス
TIMESLOTS_FILE = 'timeslots.json'
RESERVATIONS_FILE = 'reservations.json'
INITIAL_CAPACITIES_FILE = 'initial_capacities.json'

# 初期時間帯データ
DEFAULT_TIMESLOTS = [
    {"time": "10:00 - 10:30", "total": 15, "available": 15},
    {"time": "10:30 - 11:00", "total": 15, "available": 15},
    {"time": "11:00 - 11:30", "total": 15, "available": 15},
    {"time": "11:30 - 12:00", "total": 15, "available": 15},
    {"time": "12:00 - 12:30", "total": 15, "available": 15},
    {"time": "12:30 - 13:00", "total": 15, "available": 15},
    {"time": "13:00 - 13:30", "total": 15, "available": 15},
    {"time": "13:30 - 14:00", "total": 15, "available": 15},
    {"time": "14:00 - 14:30", "total": 15, "available": 15},
    {"time": "14:30 - 15:00", "total": 15, "available": 15}
]

def load_timeslots():
    """時間帯データを読み込み"""
    if os.path.exists(TIMESLOTS_FILE):
        with open(TIMESLOTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        save_timeslots(DEFAULT_TIMESLOTS)
        return DEFAULT_TIMESLOTS

def save_timeslots(timeslots):
    """時間帯データを保存"""
    with open(TIMESLOTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(timeslots, f, ensure_ascii=False, indent=2)

def load_reservations():
    """予約データを読み込み"""
    if os.path.exists(RESERVATIONS_FILE):
        with open(RESERVATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_reservations(reservations):
    """予約データを保存"""
    with open(RESERVATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reservations, f, ensure_ascii=False, indent=2)

def load_initial_capacities():
    """初期定員設定を読み込み"""
    if os.path.exists(INITIAL_CAPACITIES_FILE):
        try:
            with open(INITIAL_CAPACITIES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # デフォルト値を返す
    return [15] * len(DEFAULT_TIMESLOTS)

def save_initial_capacities(capacities):
    """初期定員設定を保存"""
    with open(INITIAL_CAPACITIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(capacities, f, ensure_ascii=False, indent=2)

def create_default_timeslots_with_capacities(capacities):
    """指定された定員で初期時間帯データを作成"""
    timeslots = []
    for i, slot_template in enumerate(DEFAULT_TIMESLOTS):
        capacity = capacities[i] if i < len(capacities) else 15
        timeslots.append({
            "time": slot_template["time"],
            "total": capacity,
            "available": capacity
        })
    return timeslots

def generate_qr_code(text):
    """QRコードを生成してBase64エンコードした文字列を返す"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def get_session_id():
    """セッションIDを取得または生成"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def get_active_reservation():
    """このセッションのアクティブな予約を取得"""
    session_id = get_session_id()
    reservations = load_reservations()
    for reservation in reversed(reservations):
        if (reservation.get('status') == 'active' and 
            reservation.get('session_id') == session_id):
            return reservation
    return None

@app.route('/')
def index():
    """トップページ（ウェルカム画面）"""
    active_reservation = get_active_reservation()
    
    if active_reservation:
        # QRコードを生成（チェックイン完了画面のURLを含める）
        qr_url = f"{request.url_root}checkin-complete?qr={active_reservation['qr_code']}"
        qr_code_data = generate_qr_code(qr_url)
        active_reservation['qr_code_image'] = qr_code_data
    
    return render_template('welcome.html', 
                         active_reservation=active_reservation)

@app.route('/reserve')
def reserve():
    """予約画面（人数選択から開始）"""
    timeslots = load_timeslots()
    active_reservation = get_active_reservation()
    
    if active_reservation:
        # QRコードを生成（チェックイン完了画面のURLを含める）
        qr_url = f"{request.url_root}checkin-complete?qr={active_reservation['qr_code']}"
        qr_code_data = generate_qr_code(qr_url)
        active_reservation['qr_code_image'] = qr_code_data
    
    return render_template('index.html', 
                         timeslots=timeslots, 
                         active_reservation=active_reservation)

@app.route('/my-ticket')
def my_ticket():
    """整理券確認画面"""
    active_reservation = get_active_reservation()
    
    if not active_reservation:
        return redirect(url_for('index'))
    
    # QRコードを生成（チェックイン完了画面のURLを含める）
    qr_url = f"{request.url_root}checkin-complete?qr={active_reservation['qr_code']}"
    qr_code_data = generate_qr_code(qr_url)
    active_reservation['qr_code_image'] = qr_code_data
    
    return render_template('my_ticket.html', 
                         active_reservation=active_reservation)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理者ログイン画面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # セッションに認証状態を保存
            session['admin_authenticated'] = True
            
            # レスポンスを作成してクッキーを設定
            response = make_response(redirect(url_for('admin')))
            
            # 24時間有効なクッキーを設定
            expires = datetime.now() + timedelta(days=1)
            response.set_cookie('admin_authenticated', 'true', 
                              expires=expires, 
                              httponly=True,
                              secure=False)  # HTTPSを使用する場合はTrueに設定
            
            return response
        else:
            return render_template('admin_login.html', error='ユーザー名またはパスワードが間違っています')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """管理者ログアウト"""
    # セッションから認証状態を削除
    session.pop('admin_authenticated', None)
    
    # レスポンスを作成してクッキーを削除
    response = make_response(redirect(url_for('admin_login')))
    response.set_cookie('admin_authenticated', '', expires=0)
    
    return response

@app.route('/admin')
@admin_required
def admin():
    """管理画面"""
    timeslots = load_timeslots()
    reservations = load_reservations()
    
    # 統計を計算
    total_reservations = len([r for r in reservations if r['status'] == 'active'])
    total_checkins = len([r for r in reservations if r['status'] == 'checked'])
    total_capacity = sum(slot['total'] for slot in timeslots)
    checkin_rate = round((total_checkins / total_reservations * 100) if total_reservations > 0 else 0)
    
    # 時間帯別統計を計算
    for slot in timeslots:
        slot_reservations = [r for r in reservations if r['time'] == slot['time'] and r['status'] in ['active', 'checked']]
        slot_checkins = [r for r in reservations if r['time'] == slot['time'] and r['status'] == 'checked']
        
        slot['reserved'] = sum(r['guests'] for r in slot_reservations)
        slot['checked'] = sum(r['guests'] for r in slot_checkins)
        slot['available'] = slot['total'] - slot['reserved']
    
    stats = {
        'total_reservations': total_reservations,
        'total_checkins': total_checkins,
        'total_capacity': total_capacity,
        'checkin_rate': checkin_rate
    }
    
    return render_template('admin.html', timeslots=timeslots, stats=stats)

@app.route('/admin/checkin')
@admin_required
def admin_checkin():
    """チェックイン画面"""
    timeslots = load_timeslots()
    reservations = load_reservations()
    
    # 各時間帯の予約リストを作成
    for slot in timeslots:
        slot['reservations'] = [r for r in reservations 
                              if r['time'] == slot['time'] and r['status'] == 'active']
    
    return render_template('admin_checkin.html', timeslots=timeslots)

@app.route('/admin/qr-checkin')
@admin_required
def qr_checkin_page():
    """QRコード読み込みページ"""
    return render_template('qr_checkin.html')

@app.route('/api/qr-checkin', methods=['POST'])
@admin_required
def api_qr_checkin():
    """QRコードによるチェックインAPI"""
    data = request.json
    qr_code = data.get('qr_code', '').strip()
    
    if not qr_code:
        return jsonify({'success': False, 'message': 'QRコードが読み取れませんでした'})
    
    reservations = load_reservations()
    
    # QRコードに該当する予約を検索
    for reservation in reservations:
        if (reservation.get('qr_code') == qr_code and 
            reservation.get('status') == 'active'):
            
            # チェックイン処理
            reservation['status'] = 'checked'
            reservation['checked_at'] = datetime.now().isoformat()
            
            save_reservations(reservations)
            
            return jsonify({
                'success': True,
                'reservation': {
                    'time': reservation['time'],
                    'guests': reservation['guests'],
                    'date': reservation['date'],
                    'qr_code': reservation['qr_code']
                }
            })
    
    return jsonify({'success': False, 'message': '有効な予約が見つかりませんでした'})

@app.route('/admin/checkin-success')
@admin_required
def checkin_success():
    """チェックイン完了画面"""
    time = request.args.get('time', '')
    guests = request.args.get('guests', '')
    qr_code = request.args.get('qr_code', '')
    
    return render_template('checkin_success.html', 
                         time=time, guests=guests, qr_code=qr_code)

@app.route('/checkin-complete')
def public_checkin_complete():
    """一般向けチェックイン完了画面（QRコードからのアクセス）"""
    qr_code = request.args.get('qr', '')
    
    if not qr_code:
        return redirect(url_for('index'))
    
    # QRコードから予約情報を取得
    reservations = load_reservations()
    reservation = None
    
    for r in reservations:
        if r.get('qr_code') == qr_code:
            reservation = r
            break
    
    if not reservation:
        return redirect(url_for('index'))
    
    # チェックイン済みでない場合は、チェックイン処理を実行
    if reservation.get('status') == 'active':
        reservation['status'] = 'checked'
        reservation['checked_at'] = datetime.now().isoformat()
        save_reservations(reservations)
    
    return render_template('public_checkin_complete.html', 
                         time=reservation['time'], 
                         guests=reservation['guests'], 
                         qr_code=reservation['qr_code'],
                         status=reservation['status'])

@app.route('/completion')
def completion():
    """完了画面"""
    time = request.args.get('time')
    guests = request.args.get('guests')
    
    return render_template('completion.html', time=time, guests=guests)

# API エンドポイント
@app.route('/api/timeslots/<int:guests>')
def api_timeslots_by_guests(guests):
    """人数に基づいて利用可能な時間帯を取得するAPI"""
    timeslots = load_timeslots()
    # 指定された人数で予約可能な時間帯のみをフィルタリング
    available_timeslots = [slot for slot in timeslots if slot['available'] >= guests]
    return jsonify({'timeslots': available_timeslots})

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    """予約作成API"""
    data = request.json
    time = data.get('time')
    guests = int(data.get('guests', 1))
    
    # 時間帯データを更新
    timeslots = load_timeslots()
    for slot in timeslots:
        if slot['time'] == time:
            if slot['available'] >= guests:
                slot['available'] -= guests
                break
            else:
                return jsonify({'success': False, 'message': '空きが不足しています'})
    
    # このセッションの既存のアクティブな予約をキャンセル
    session_id = get_session_id()
    reservations = load_reservations()
    for reservation in reservations:
        if (reservation.get('status') == 'active' and 
            reservation.get('session_id') == session_id):
            reservation['status'] = 'cancelled'
    
    # 新しい予約を追加
    qr_code_text = f"QR-{time.replace(':', '').replace(' ', '').replace('-', '')}-{guests}-{session_id[:8]}"
    reservation = {
        'time': time,
        'guests': guests,
        'date': datetime.now().strftime('%Y/%m/%d'),
        'status': 'active',
        'qr_code': qr_code_text,
        'session_id': session_id,
        'created_at': datetime.now().isoformat()
    }
    reservations.append(reservation)
    
    # データを保存
    save_timeslots(timeslots)
    save_reservations(reservations)
    
    # QRコードを生成（チェックイン完了画面のURLを含める）
    qr_url = f"{request.url_root}checkin-complete?qr={qr_code_text}"
    qr_code_image = generate_qr_code(qr_url)
    reservation['qr_code_image'] = qr_code_image
    
    return jsonify({'success': True, 'reservation': reservation})

@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    """予約キャンセルAPI"""
    session_id = get_session_id()
    reservations = load_reservations()
    timeslots = load_timeslots()
    
    # このセッションのアクティブな予約を見つけてキャンセル
    for reservation in reversed(reservations):
        if (reservation.get('status') == 'active' and 
            reservation.get('session_id') == session_id):
            reservation['status'] = 'cancelled'
            
            # 時間帯の空きを戻す
            for slot in timeslots:
                if slot['time'] == reservation['time']:
                    slot['available'] += reservation['guests']
                    break
            
            # データを保存
            save_timeslots(timeslots)
            save_reservations(reservations)
            
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'アクティブな予約が見つかりません'})

@app.route('/api/checkin', methods=['POST'])
@admin_required
def api_checkin():
    """チェックインAPI"""
    data = request.json
    time = data.get('time')
    guests = int(data.get('guests', 1))
    
    reservations = load_reservations()
    
    # 該当する予約を見つけてチェックイン（任意のセッションから）
    for reservation in reservations:
        if (reservation['time'] == time and 
            reservation['guests'] == guests and 
            reservation['status'] == 'active'):
            reservation['status'] = 'checked'
            reservation['checked_at'] = datetime.now().isoformat()
            
            save_reservations(reservations)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': '該当する予約が見つかりません'})

@app.route('/api/update_capacity', methods=['POST'])
@admin_required
def api_update_capacity():
    """定員数更新API"""
    data = request.json
    index = int(data.get('index'))
    new_total = int(data.get('total'))
    
    timeslots = load_timeslots()
    if 0 <= index < len(timeslots):
        old_total = timeslots[index]['total']
        timeslots[index]['total'] = new_total
        
        # 利用可能数も調整
        diff = new_total - old_total
        timeslots[index]['available'] += diff
        
        save_timeslots(timeslots)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': '無効なインデックスです'})

@app.route('/api/reset_reservations', methods=['POST'])
@admin_required
def api_reset_reservations():
    """予約データ初期化API"""
    try:
        # 予約データを空の配列で初期化
        save_reservations([])
        
        # 時間帯の利用可能数をリセット
        timeslots = load_timeslots()
        for slot in timeslots:
            slot['available'] = slot['total']
        save_timeslots(timeslots)
        
        return jsonify({'success': True, 'message': '予約データを初期化しました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'初期化に失敗しました: {str(e)}'})

@app.route('/api/reset_timeslots', methods=['POST'])
@admin_required
def api_reset_timeslots():
    """時間帯データ初期化API"""
    try:
        # 保存された初期定員設定を使用
        initial_capacities = load_initial_capacities()
        timeslots = create_default_timeslots_with_capacities(initial_capacities)
        save_timeslots(timeslots)
        
        return jsonify({'success': True, 'message': '時間帯データを初期化しました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'初期化に失敗しました: {str(e)}'})

@app.route('/api/reset_all_data', methods=['POST'])
@admin_required
def api_reset_all_data():
    """全データ初期化API"""
    try:
        # 予約データを空の配列で初期化
        save_reservations([])
        
        # 保存された初期定員設定を使用して時間帯データを初期化
        initial_capacities = load_initial_capacities()
        timeslots = create_default_timeslots_with_capacities(initial_capacities)
        save_timeslots(timeslots)
        
        return jsonify({'success': True, 'message': '全データを初期化しました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'初期化に失敗しました: {str(e)}'})

@app.route('/api/update_initial_capacities', methods=['POST'])
@admin_required
def api_update_initial_capacities():
    """初期定員設定更新API"""
    try:
        data = request.json
        capacities_data = data.get('capacities', [])
        
        # 定員リストを作成
        capacities = [15] * len(DEFAULT_TIMESLOTS)  # デフォルト値で初期化
        for item in capacities_data:
            index = item.get('index')
            capacity = item.get('capacity', 15)
            if 0 <= index < len(capacities):
                capacities[index] = max(0, min(50, capacity))  # 0-50の範囲に制限
        
        save_initial_capacities(capacities)
        return jsonify({'success': True, 'message': '初期定員設定を保存しました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存に失敗しました: {str(e)}'})

@app.route('/api/reset_to_default_capacities', methods=['POST'])
@admin_required
def api_reset_to_default_capacities():
    """初期定員をデフォルト値にリセットAPI"""
    try:
        default_capacities = [15] * len(DEFAULT_TIMESLOTS)
        save_initial_capacities(default_capacities)
        return jsonify({'success': True, 'message': '初期定員をデフォルト値にリセットしました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'リセットに失敗しました: {str(e)}'})

@app.route('/api/set_bulk_initial_capacity', methods=['POST'])
@admin_required
def api_set_bulk_initial_capacity():
    """全時間帯の初期定員を一括設定API"""
    try:
        data = request.json
        capacity = int(data.get('capacity', 15))
        
        # 定員値の範囲チェック
        capacity = max(0, min(50, capacity))
        
        # 全時間帯を同じ定員に設定
        bulk_capacities = [capacity] * len(DEFAULT_TIMESLOTS)
        save_initial_capacities(bulk_capacities)
        
        return jsonify({'success': True, 'message': f'全時間帯の初期定員を{capacity}名に設定しました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'一括設定に失敗しました: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, port=8000) 