# 📚 デュアルリポジトリ管理ガイド

このプロジェクトは、**パブリックリポジトリ**と**プライベートリポジトリ**の2つのリポジトリで管理されています。

## 🌐 パブリックリポジトリ (trading-bot-public)
- **目的**: インフラ・骨格部分の公開
- **除外対象**: MLアルゴリズム、戦略実装、機密データ
- **対象者**: 学習・参考・コラボレーション

## 🔒 プライベートリポジトリ (trading-bot-live)
- **目的**: 完全なコードベースの保存
- **含む対象**: 全ファイル（MLモデル、アルゴリズム、ドキュメント）
- **対象者**: 開発者本人のみ

## 📋 リポジトリ構成

### パブリックリポジトリに含まれるファイル
```
├── README.md                    # プロジェクト概要
├── requirements.txt             # 依存関係
├── docker-compose.yml          # インフラ設定
├── Dockerfile.dev              # 開発環境
├── Makefile                    # タスク自動化
├── .env.template               # 環境変数テンプレート
├── .github/workflows/ci.yml    # CI/CD設定
├── postgres/init/              # DB初期化
├── scripts/
│   ├── etl_nightly.sh         # ETLバッチ
│   └── fetch_prices_daily.py  # データ取得
└── src/data/                   # データクライアント
    └── jquants_client.py
```

### プライベートリポジトリに追加で含まれるファイル
```
├── specification.txt           # 設計書（機密）
├── project_documentation.html # 詳細ドキュメント
├── src/models/                 # MLモデル実装
│   └── rank_transformer.py    # Transformerモデル
├── tests/                      # MLモデルテスト
│   └── test_rank_transformer.py
├── algorithms/                 # アルゴリズム（今後）
├── strategies/                 # 戦略実装（今後）
└── *.pkl, *.pt, *.pth         # 学習済みモデル
```

## 🔄 同期スクリプト

### 1. プライベートリポジトリに同期
```bash
./sync-private.sh
```
- 全ファイル（MLアルゴリズム含む）をプライベートリポジトリに同期
- 完全バックアップとして機能

### 2. パブリックリポジトリに同期
```bash
./sync-public.sh
```
- 機密ファイルを除外してパブリックリポジトリに同期
- インフラ・骨格部分のみ公開

## 📝 使用方法

### 日常的な開発作業
1. 通常通りコードを開発
2. MLモデルやアルゴリズムも含めて自由に実装
3. 定期的に `./sync-private.sh` で完全バックアップ
4. 必要に応じて `./sync-public.sh` でパブリック部分を更新

### 新しいMLモデルを追加する場合
1. `src/models/` にモデルファイルを作成
2. `tests/` にテストファイルを作成
3. `.gitignore` により自動的にパブリックリポジトリから除外
4. プライベートリポジトリには `./sync-private.sh` で同期

## 🔧 セットアップ

### 初回セットアップ
```bash
# リモートリポジトリの確認
git remote -v

# 出力例:
# origin  https://github.com/Taku-Ohsaki/trading-bot-public.git (fetch)
# origin  https://github.com/Taku-Ohsaki/trading-bot-public.git (push)  
# private https://github.com/Taku-Ohsaki/trading-bot-live.git (fetch)
# private https://github.com/Taku-Ohsaki/trading-bot-live.git (push)
```

### 同期スクリプトの実行可能化
```bash
chmod +x sync-private.sh sync-public.sh
```

## ⚠️ 注意事項

1. **機密データの保護**: プライベートリポジトリのURLや内容を外部に共有しない
2. **同期の順序**: 開発後は必ずプライベートリポジトリを先に同期
3. **.gitignore の管理**: 2つの異なる .gitignore ファイルを使用
   - `.gitignore`: パブリック用（多くのファイルを除外）
   - `.gitignore-private`: プライベート用（最小限の除外）

## 🚀 今後の拡張

- 自動同期スクリプトの実装
- CI/CD パイプラインでの自動同期
- ブランチ戦略の最適化
- セキュリティ監査の自動化