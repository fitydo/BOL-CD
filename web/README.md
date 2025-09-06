# BOL-CD Web Dashboard

React製のWeb UIダッシュボード。アラート削減の監視と管理を提供します。

## 機能

- 📊 **リアルタイムダッシュボード**: 削減率、誤抑制率、処理イベント数の表示
- 🎯 **アラート削減管理**: ML最適化パラメータの調整と実行
- 📝 **ルール管理**: 削減ルールのCRUD操作
- 📈 **レポート表示**: 日次・週次レポートの閲覧
- ⚙️ **設定管理**: API接続、SIEM連携の設定

## 技術スタック

- **React 18**: UIフレームワーク
- **TypeScript**: 型安全性
- **Tailwind CSS**: スタイリング
- **Recharts**: グラフ表示
- **Vite**: ビルドツール
- **Axios**: API通信

## セットアップ

### 開発環境

```bash
# 依存関係のインストール
cd web
npm install

# 開発サーバー起動（http://localhost:3000）
npm run dev
```

### 環境変数

`.env`ファイルを作成:

```env
REACT_APP_API_URL=http://localhost:8080
REACT_APP_API_KEY=viewer:your-api-key
```

### ビルド

```bash
# プロダクションビルド
npm run build

# ビルド結果のプレビュー
npm run preview
```

## ディレクトリ構成

```
web/
├── src/
│   ├── components/      # 共通コンポーネント
│   │   ├── Layout.tsx   # レイアウト（サイドバー）
│   │   ├── StatsCard.tsx # 統計カード
│   │   ├── ReductionChart.tsx # 削減率グラフ
│   │   └── AlertsTable.tsx # アラートテーブル
│   ├── contexts/        # React Context
│   │   └── ApiContext.tsx # API通信管理
│   ├── pages/          # ページコンポーネント
│   │   ├── Dashboard.tsx # ダッシュボード
│   │   ├── AlertReduction.tsx # アラート削減
│   │   ├── Rules.tsx    # ルール管理
│   │   ├── Reports.tsx  # レポート
│   │   └── Settings.tsx # 設定
│   ├── App.tsx         # メインApp
│   ├── main.tsx        # エントリーポイント
│   └── index.css       # グローバルCSS
├── public/             # 静的ファイル
├── package.json        # 依存関係
├── vite.config.ts      # Vite設定
├── tailwind.config.js  # Tailwind設定
└── tsconfig.json       # TypeScript設定
```

## API連携

Web UIは以下のAPIエンドポイントと通信:

- `GET /metrics` - Prometheusメトリクス取得
- `GET /api/reports/daily/latest` - 最新レポート
- `GET /api/rules` - ルール一覧
- `POST /api/edges/recompute` - 最適化実行
- `GET /api/graph` - グラフデータ取得

## デプロイ

### Dockerでのデプロイ

```dockerfile
# web/Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Nginxプロキシ設定

```nginx
server {
    listen 80;
    server_name localhost;
    
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
    
    location /api {
        proxy_pass http://bolcd-api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 今後の拡張予定

- [ ] WebSocket対応（リアルタイム更新）
- [ ] ダークモード対応
- [ ] 多言語対応（i18n）
- [ ] グラフのインタラクティブ機能強化
- [ ] エクスポート機能（PDF/CSV）
- [ ] ユーザー認証統合（OIDC/SAML）

## ライセンス

MIT License
