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
ADMIN_USERNAME = '2-5'
ADMIN_PASSWORD = '1234'

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

# 初期時間帯データ（日付別）
DEFAULT_TIMESLOTS = {
    "2025-06-27": [
        {"time": "13:15 - 13:45", "total": 15, "available": 15},
        {"time": "13:45 - 14:15", "total": 15, "available": 15},
        {"time": "14:15 - 14:45", "total": 15, "available": 15},
        {"time": "14:45 - 15:15", "total": 15, "available": 15},
        {"time": "15:15 - 15:45", "total": 15, "available": 15},
        {"time": "15:45 - 16:15", "total": 15, "available": 15}
    ],
    "2025-06-28": [
        {"time": "11:20 - 11:50", "total": 15, "available": 15},
        {"time": "11:50 - 12:20", "total": 15, "available": 15},
        {"time": "12:20 - 12:50", "total": 15, "available": 15},
        {"time": "12:50 - 13:20", "total": 15, "available": 15},
        {"time": "13:20 - 13:50", "total": 15, "available": 15},
        {"time": "13:50 - 14:20", "total": 15, "available": 15},
        {"time": "14:20 - 14:50", "total": 15, "available": 15},
        {"time": "14:50 - 15:20", "total": 15, "available": 15},
        {"time": "15:20 - 15:50", "total": 15, "available": 15}
    ]
}

def get_today_date():
    """当日の日付を取得（6月27日または28日）"""
    today = datetime.now()
    if today.month == 6 and today.day in [27, 28]:
        return today.strftime('%Y-%m-%d')
    else:
        # テスト用：27日をデフォルトに（実際の運用では日付チェックを厳密に）
        return '2025-06-27'

def load_timeslots(date=None):
    """指定日付の時間帯データを読み込み"""
    if date is None:
        date = get_today_date()
    
    if os.path.exists(TIMESLOTS_FILE):
        try:
            with open(TIMESLOTS_FILE, 'r', encoding='utf-8') as f:
                all_timeslots = json.load(f)
            # データが辞書形式であることを確認
            if isinstance(all_timeslots, dict):
                return all_timeslots.get(date, [])
        except (json.JSONDecodeError, FileNotFoundError):
            # ファイルが空、破損、または存在しない場合は、デフォルト値で再生成
            pass

    # ファイルが存在しない、またはデータ形式が不正な場合はデフォルト値を使用
    print(f"警告: {TIMESLOTS_FILE} が不正、または存在しません。デフォルト値で再生成します。")
    save_timeslots(DEFAULT_TIMESLOTS)
    return DEFAULT_TIMESLOTS.get(date, [])

def save_timeslots(all_timeslots):
    """時間帯データを保存"""
    with open(TIMESLOTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_timeslots, f, ensure_ascii=False, indent=2)

def save_timeslots_for_date(date, timeslots):
    """指定日付の時間帯データを保存"""
    if os.path.exists(TIMESLOTS_FILE):
        with open(TIMESLOTS_FILE, 'r', encoding='utf-8') as f:
            all_timeslots = json.load(f)
    else:
        all_timeslots = DEFAULT_TIMESLOTS.copy()
    
    all_timeslots[date] = timeslots
    save_timeslots(all_timeslots)

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
    today_date = get_today_date()
    active_reservation = get_active_reservation()
    
    if active_reservation:
        # QRコードを生成（チェックイン完了画面のURLを含める）
        qr_url = f"{request.url_root}checkin-complete?qr={active_reservation['qr_code']}"
        qr_code_data = generate_qr_code(qr_url)
        active_reservation['qr_code_image'] = qr_code_data
    
    return render_template('welcome.html', 
                         active_reservation=active_reservation,
                         today_date=today_date)

@app.route('/reserve')
def reserve():
    """予約画面（人数選択から開始）"""
    today_date = get_today_date()
    timeslots = load_timeslots(today_date)
    active_reservation = get_active_reservation()
    
    if active_reservation:
        # QRコードを生成（チェックイン完了画面のURLを含める）
        qr_url = f"{request.url_root}checkin-complete?qr={active_reservation['qr_code']}"
        qr_code_data = generate_qr_code(qr_url)
        active_reservation['qr_code_image'] = qr_code_data
    
    return render_template('index.html', 
                         timeslots=timeslots, 
                         active_reservation=active_reservation,
                         today_date=today_date)

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
    # 管理画面では日付を選択可能
    selected_date = request.args.get('date', get_today_date())
    
    # 有効な日付のみ許可
    valid_dates = ['2025-06-27', '2025-06-28']
    if selected_date not in valid_dates:
        selected_date = get_today_date()
    
    timeslots = load_timeslots(selected_date)
    reservations = load_reservations()
    
    # 選択された日付の予約のみを対象とする
    date_reservations = [r for r in reservations if r.get('date') == selected_date.replace('-', '/')]
    
    # 統計を計算
    total_reservations = len([r for r in date_reservations if r['status'] == 'active'])
    total_checkins = len([r for r in date_reservations if r['status'] == 'checked'])
    total_capacity = sum(slot['total'] for slot in timeslots)
    checkin_rate = round((total_checkins / total_reservations * 100) if total_reservations > 0 else 0)
    
    # 時間帯別統計を計算
    for slot in timeslots:
        slot_reservations = [r for r in date_reservations if r['time'] == slot['time'] and r['status'] in ['active', 'checked']]
        slot_checkins = [r for r in date_reservations if r['time'] == slot['time'] and r['status'] == 'checked']
        
        slot['reserved'] = sum(r['guests'] for r in slot_reservations)
        slot['checked'] = sum(r['guests'] for r in slot_checkins)
        slot['available'] = slot['total'] - slot['reserved']
    
    stats = {
        'total_reservations': total_reservations,
        'total_checkins': total_checkins,
        'total_capacity': total_capacity,
        'checkin_rate': checkin_rate
    }
    
    return render_template('admin.html', 
                         timeslots=timeslots, 
                         stats=stats, 
                         selected_date=selected_date,
                         valid_dates=valid_dates)

@app.route('/admin/checkin')
@admin_required
def admin_checkin():
    """チェックイン画面"""
    # 管理画面では日付を選択可能
    selected_date = request.args.get('date', get_today_date())
    
    # 有効な日付のみ許可
    valid_dates = ['2025-06-27', '2025-06-28']
    if selected_date not in valid_dates:
        selected_date = get_today_date()
        
    timeslots = load_timeslots(selected_date)
    reservations = load_reservations()
    
    # 選択された日付の予約のみを対象とする
    date_reservations = [r for r in reservations if r.get('date') == selected_date.replace('-', '/')]
    
    # 各時間帯の予約リストを作成
    for slot in timeslots:
        slot['reservations'] = [r for r in date_reservations 
                              if r['time'] == slot['time'] and r['status'] == 'active']
    
    return render_template('admin_checkin.html', 
                         timeslots=timeslots, 
                         selected_date=selected_date,
                         valid_dates=valid_dates)

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
        
        # ログ出力
        print(f"[QR受付完了] 時間: {reservation['time']}, 人数: {reservation['guests']}名, QR: {reservation['qr_code']}")
        
        save_reservations(reservations)
    else:
        # 既にチェックイン済みの場合のログ
        print(f"[QR確認] 既にチェックイン済み - QR: {reservation['qr_code']}")
    
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
    today_date = get_today_date()
    timeslots = load_timeslots(today_date)
    # 指定された人数で予約可能な時間帯のみをフィルタリング
    available_timeslots = [slot for slot in timeslots if slot['available'] >= guests]
    return jsonify({'timeslots': available_timeslots, 'date': today_date})

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    """予約作成API"""
    # FormDataまたはJSONデータを処理
    if request.content_type and 'multipart/form-data' in request.content_type:
        time = request.form.get('time')
        guests = int(request.form.get('guests', 1))
        image_file = request.files.get('image')
    else:
        data = request.json
        time = data.get('time')
        guests = int(data.get('guests', 1))
        image_file = None
    
    today_date = get_today_date()
    
    # 時間帯データを更新
    timeslots = load_timeslots(today_date)
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
    
    # 画像を保存（アップロードされた場合）
    image_path = None
    if image_file and image_file.filename:
        # 画像ファイル用のディレクトリを作成
        upload_dir = os.path.join('static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイル名を生成（セッションIDとタイムスタンプを使用）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = os.path.splitext(image_file.filename)[1]
        filename = f"{session_id[:8]}_{timestamp}{file_extension}"
        image_path = os.path.join(upload_dir, filename)
        
        try:
            image_file.save(image_path)
            # Webアクセス用のパスに変換
            image_url = f"/static/uploads/{filename}"
        except Exception as e:
            print(f"画像保存エラー: {e}")
            image_url = None
    else:
        image_url = None

    # 新しい予約を追加
    qr_code_text = f"QR-{time.replace(':', '').replace(' ', '').replace('-', '')}-{guests}-{session_id[:8]}"
    reservation = {
        'time': time,
        'guests': guests,
        'date': today_date.replace('-', '/'),
        'status': 'active',
        'qr_code': qr_code_text,
        'session_id': session_id,
        'created_at': datetime.now().isoformat(),
        'user_image': image_url
    }
    reservations.append(reservation)
    
    # データを保存
    save_timeslots_for_date(today_date, timeslots)
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
    today_date = get_today_date()
    timeslots = load_timeslots(today_date)
    
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
            save_timeslots_for_date(today_date, timeslots)
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
        # 時間帯データをデフォルト値で初期化
        save_timeslots(DEFAULT_TIMESLOTS.copy())
        
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
        
        # 時間帯データをデフォルト値で初期化
        save_timeslots(DEFAULT_TIMESLOTS.copy())
        
        return jsonify({'success': True, 'message': '全データを初期化しました'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'初期化に失敗しました: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, port=8000) 