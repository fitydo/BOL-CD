export default {
  // Authentication
  auth: {
    login: {
      title: 'ログイン',
      subtitle: 'アカウントにログインしてください',
      submit: 'ログイン'
    },
    signup: {
      title: '新規登録',
      subtitle: '新しいアカウントを作成',
      submit: '登録'
    },
    field: {
      email: 'メールアドレス',
      username: 'ユーザー名',
      password: 'パスワード',
      confirmPassword: 'パスワード（確認）',
      fullName: '氏名'
    },
    googleSignIn: 'Googleでログイン',
    or: 'または',
    switchToLogin: 'すでにアカウントをお持ちですか？ログイン',
    switchToSignup: 'アカウントをお持ちでないですか？新規登録',
    loading: '処理中...',
    error: {
      generic: 'エラーが発生しました',
      googleNotConfigured: 'Google認証が設定されていません',
      googleFailed: 'Google認証に失敗しました'
    },
    demoAccounts: 'テスト用デモアカウント',
    demoNote: 'クリックして認証情報を自動入力'
  },
  
  // Account
  account: {
    title: 'アカウント設定',
    profile: 'プロフィール',
    security: 'セキュリティ',
    memberSince: '登録日',
    email: 'メールアドレス',
    username: 'ユーザー名',
    fullName: '氏名',
    authProvider: '認証プロバイダー',
    role: '権限',
    lastLogin: '最終ログイン',
    verified: '認証済み',
    edit: '編集',
    save: '保存',
    changePassword: 'パスワード変更',
    currentPassword: '現在のパスワード',
    newPassword: '新しいパスワード',
    confirmNewPassword: '新しいパスワード（確認）',
    logout: 'ログアウト',
    deleteAccount: 'アカウント削除',
    deleteAccountConfirm: 'アカウント削除の確認',
    deleteAccountWarning: 'この操作は取り消せません。すべてのデータが削除されます。',
    deleteConfirm: '削除する',
    updateSuccess: 'プロフィールを更新しました',
    updateError: 'プロフィールの更新に失敗しました',
    passwordChanged: 'パスワードを変更しました',
    passwordChangeError: 'パスワードの変更に失敗しました',
    passwordMismatch: 'パスワードが一致しません',
    deleteError: 'アカウントの削除に失敗しました'
  },
  
  // Navigation
  nav: {
    dashboard: 'ダッシュボード',
    alertReduction: 'アラート削減',
    rules: 'ルール管理',
    reports: 'レポート',
    pricing: '料金プラン',
    settings: '設定',
    account: 'アカウント'
  },
  
  // Dashboard
  dashboard: {
    title: 'ダッシュボード',
    subtitle: 'アラート削減システムの現在の状態',
    
    stats: {
      reductionRate: 'アラート削減率',
      falseSuppressionRate: '誤抑制率',
      processedEvents: '処理イベント数',
      activeRules: 'アクティブルール',
      targetAchieved: '目標達成',
      improving: '改善中',
      safetyEnsured: '安全性確保',
      last24Hours: '過去24時間',
      enabled: '有効'
    },
    
    charts: {
      reductionTrend: '削減率推移',
      latestAlerts: '最新のアラート',
      reduction: '削減率',
      target: '目標'
    },
    
    alerts: {
      actionRequired: '対応が必要なアラート',
      noUrgentAlerts: '現在、緊急対応が必要なアラートはありません',
      openSOC: 'SOCダッシュボードを開く',
      checkSIEM: 'SIEMで確認',
      details: '詳細',
      count: '{{count}}件'
    },
    
    summary: {
      title: '本日のサマリー',
      suppressedCount: '過去24時間で {{count}} 件のアラートを削減しました。',
      reductionRate: '削減率は {{rate}}% で、',
      targetAchieved: '目標の50%を達成',
      targetProgress: '目標の50%に向けて改善中',
      topCategories: '主な削減カテゴリ:',
      events: '件'
    }
  },
  
  // Alert Reduction
  alertReduction: {
    title: 'アラート削減',
    subtitle: '機械学習による自動削減の設定と実行',
    
    settings: {
      title: '最適化設定',
      targetReduction: '目標削減率',
      targetReductionHelp: '0.6 = 60%削減',
      epsilon: 'イプシロン (ε)',
      epsilonHelp: '含意検出の閾値',
      fdrQ: 'FDR q値',
      fdrQHelp: '偽発見率制御',
      eventsPath: 'イベントファイルパス',
      optimize: '最適化実行'
    },
    
    status: {
      title: '現在の削減状況',
      reductionRate: '削減率',
      suppressedEvents: '削減イベント数',
      falseSuppressionRate: '誤抑制率',
      topCategories: '主な削減カテゴリ'
    }
  },
  
  // Rules
  rules: {
    title: 'ルール管理',
    subtitle: 'アラート削減ルールの設定と管理',
    newRule: '新規ルール',
    noRules: 'ルールがありません',
    
    table: {
      name: 'ルール名',
      description: '説明',
      severity: '重要度',
      status: '状態',
      enabled: '有効',
      disabled: '無効',
      actions: 'アクション'
    },
    
    modal: {
      create: '新規ルール作成',
      edit: 'ルール編集',
      name: 'ルール名',
      description: '説明',
      severity: '重要度',
      save: '保存',
      cancel: 'キャンセル'
    }
  },
  
  // Reports
  reports: {
    title: 'レポート',
    subtitle: '日次・週次レポートの閲覧とエクスポート',
    
    period: {
      daily: '日次',
      weekly: '週次',
      monthly: '月次'
    },
    
    summary: {
      avgReduction: '平均削減率',
      totalSuppressed: '総削減アラート数',
      totalProcessed: '処理イベント数',
      last7Days: '過去7日間'
    },
    
    history: {
      title: 'レポート履歴',
      date: '日付',
      type: 'タイプ',
      reductionRate: '削減率',
      processedEvents: '処理イベント',
      suppressedAlerts: '削減アラート',
      status: '状態',
      completed: '完了',
      details: '詳細'
    },
    
    export: {
      csv: 'CSV',
      json: 'JSON',
      pdf: 'PDF',
      message: 'レポートを{{format}}形式でエクスポートします'
    },
    
    chart: {
      title: '削減率トレンド',
      placeholder: 'グラフコンポーネント（Rechartsを使用して実装）'
    }
  },
  
  // Settings
  settings: {
    title: '設定',
    subtitle: 'システム設定とAPI連携の管理',
    save: '設定を保存',
    saved: '保存しました',
    
    tabs: {
      general: '一般',
      api: 'API',
      siem: 'SIEM連携',
      notifications: '通知',
      security: 'セキュリティ'
    },
    
    general: {
      organizationName: '組織名',
      timezone: 'タイムゾーン',
      language: '言語',
      languageHelp: 'UIの表示言語を変更します。変更は即座に反映されます。'
    },
    
    api: {
      url: 'API URL',
      key: 'APIキー',
      rateLimit: 'レート制限 (req/sec)',
      timeout: 'タイムアウト (秒)'
    },
    
    siem: {
      title: 'SIEM連携設定',
      enableSplunk: 'Splunk連携を有効化',
      enableSentinel: 'Azure Sentinel連携を有効化',
      enableOpenSearch: 'OpenSearch連携を有効化'
    },
    
    notifications: {
      email: 'メール通知',
      emailDesc: '重要なアラートをメールで受信',
      slack: 'Slack通知',
      slackDesc: 'Slackチャンネルに通知を送信'
    },
    
    security: {
      mfa: '多要素認証（MFA）',
      mfaDesc: 'ログイン時の追加認証',
      sessionTimeout: 'セッションタイムアウト（分）',
      ipWhitelist: 'IPホワイトリスト（カンマ区切り）',
      auditLogRetention: '監査ログ保持期間（日）'
    }
  },
  
  // Common
  common: {
    loading: '読み込み中...',
    error: 'エラー',
    success: '成功',
    warning: '警告',
    info: '情報',
    confirm: '確認',
    cancel: 'キャンセル',
    save: '保存',
    delete: '削除',
    edit: '編集',
    add: '追加',
    search: '検索',
    filter: 'フィルター',
    export: 'エクスポート',
    import: 'インポート',
    refresh: '更新',
    actions: 'アクション'
  },
  
  // Severity levels
  severity: {
    critical: 'CRITICAL',
    high: 'HIGH',
    medium: 'MEDIUM',
    low: 'LOW',
    info: 'INFO'
  }
};