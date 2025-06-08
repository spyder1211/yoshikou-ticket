# 海底二万マイル 整理券予約システム (Flask版)

## 概要
「海底二万マイル」という体験型施設の整理券予約システムのPython Flask版です。
時間帯別の予約管理、QRコード付き整理券発行、管理機能を提供します。

## 機能
- **予約システム**: 時間帯選択、人数選択、QRコード付き整理券発行
- **管理画面**: 統計表示、時間帯別状況確認、定員数管理
- **チェックイン機能**: 来場者のチェックイン処理
- **キャンセル機能**: 予約のキャンセル処理
- **データ永続化**: JSONファイルによるデータ管理

## セットアップ手順

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. アプリケーションの起動
```bash
python app.py
```

### 3. アクセス
- 予約画面: http://localhost:5000/
- 管理画面: http://localhost:5000/admin

## ファイル構成
```
├── app.py                    # メインアプリケーション
├── requirements.txt          # 依存関係
├── timeslots.json           # 時間帯データ
├── reservations.json        # 予約データ
├── templates/               # HTMLテンプレート
│   ├── base.html           # ベーステンプレート
│   ├── index.html          # 予約画面
│   ├── admin.html          # 管理画面
│   ├── admin_checkin.html  # チェックイン画面
│   └── completion.html     # 完了画面
└── README.md               # このファイル
```

## API エンドポイント
- `POST /api/reserve` - 予約作成
- `POST /api/cancel` - 予約キャンセル
- `POST /api/checkin` - チェックイン
- `POST /api/update_capacity` - 定員数更新

## データ管理
- **timeslots.json**: 時間帯の定員と空き状況
- **reservations.json**: 予約履歴（active/cancelled/checked）

## 注意事項
- 1回の実行につき1つのアクティブな予約のみ保持
- QRコードは時間帯と人数に基づいて生成
- 管理画面は5秒間隔で自動更新
- データはJSONファイルに永続化されます

## 開発者向け
- Flask開発モードで実行（`debug=True`）
- テンプレートエンジン: Jinja2
- QRコード生成: qrcode + Pillow
- レスポンシブデザイン対応 