# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

「海底二万マイル」体験型施設の整理券予約システム（Flask版）。時間帯別予約管理、QRコード付き整理券発行、管理者認証、チェックイン機能を持つWebアプリケーション。複数ユーザーの同時利用に対応したセッション管理を実装。

## 開発・運用コマンド

### 基本的な開発コマンド
```bash
# 依存関係のインストール
pip install -r requirements.txt

# アプリケーション起動（開発モード）
python main.py

# 手動でのJSONファイル確認
cat timeslots.json    # 時間帯データ
cat reservations.json # 予約データ
```

### アクセス URL
- **一般ユーザー**: http://localhost:8000/
- **管理者ログイン**: http://localhost:8000/admin/login
- **管理画面**: http://localhost:8000/admin （認証必要）

### 管理者認証情報
- ユーザー名: `admin`
- パスワード: `password123`

## アーキテクチャ構成

### データフロー
1. **セッション管理**: UUIDベースのセッションID（31日有効）で複数ユーザーを識別
2. **予約フロー**: セッション単位でactive予約を1つのみ保持、新規予約時は既存をcancel
3. **QRコード生成**: 予約情報 + セッションIDベースでユニークなQR文字列を生成
4. **チェックイン**: QRコードスキャンまたは管理者手動でactive→checked状態に変更

### データ永続化
- **timeslots.json**: 時間帯別の定員と空き状況管理
- **reservations.json**: 全予約履歴（status: active/cancelled/checked）

### 認証システム
- **二重認証**: Flaskセッション + HTTPクッキー（24時間有効）
- **管理者機能**: `@admin_required`デコレータによるアクセス制御

### セッション分離設計
各ユーザーセッションは完全に独立して動作：
- セッションIDで予約を分離（main.py:97-111）
- 同一セッション内での予約重複を防止（main.py:362-368）
- 管理画面では全セッションのデータを集約表示（main.py:206-225）

### QRコード機能
- **生成**: `QR-{時間}-{人数}-{セッションID8桁}`形式
- **URL埋め込み**: `/checkin-complete?qr={qr_code}`でパブリックチェックイン画面へ誘導
- **自動チェックイン**: QRアクセス時に未チェックインなら自動的にchecked状態に変更

## 重要な実装パターン

### 予約状態管理
```python
# セッション内のactive予約を取得（main.py:103-111）
def get_active_reservation():
    session_id = get_session_id()
    # 最新の予約から逆順検索でactive状態を見つける
```

### 時間帯空き数計算
管理画面では動的に計算（main.py:212-218）：
- `reserved` = active + checked状態の予約人数合計
- `available` = total - reserved
- `checked` = checked状態のみの人数合計

### デコレータベース認証
```python
@admin_required  # main.py:20-34
def admin_function():
    # セッション + クッキー両方で認証確認
```

## フロントエンド構成

### テンプレート階層
- **base.html**: 共通レイアウト
- **welcome.html**: ランディングページ（予約状況に応じて表示切替）
- **index.html**: 予約画面（人数選択→時間帯選択）
- **admin.html**: 管理画面（統計 + 時間帯別詳細、5秒自動更新）

### CSS構成
- **base.css**: 共通スタイル、レスポンシブ対応
- **style.css**: ページ固有スタイル

## セキュリティ考慮事項

- **本番環境では必須**: `app.secret_key`、管理者パスワード、HTTPS設定の変更
- **QRコード**: セッションID部分文字列により推測困難性を確保
- **認証クッキー**: httponly=True、本番ではsecure=True必須

## トラブルシューティング

### よくある問題
1. **空き数が負の値**: timeslots.jsonとreservations.jsonの整合性確認
2. **QRコード読み取り失敗**: qr_code文字列の完全一致確認
3. **セッション消失**: ブラウザクッキー削除により新セッション生成