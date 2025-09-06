export default {
  // Authentication
  auth: {
    login: {
      title: 'Sign In',
      subtitle: 'Sign in to your account',
      submit: 'Sign In'
    },
    signup: {
      title: 'Sign Up',
      subtitle: 'Create a new account',
      submit: 'Sign Up'
    },
    field: {
      email: 'Email Address',
      username: 'Username',
      password: 'Password',
      confirmPassword: 'Confirm Password',
      fullName: 'Full Name'
    },
    googleSignIn: 'Sign in with Google',
    or: 'or',
    switchToLogin: 'Already have an account? Sign in',
    switchToSignup: "Don't have an account? Sign up",
    loading: 'Processing...',
    error: {
      generic: 'An error occurred',
      googleNotConfigured: 'Google authentication is not configured',
      googleFailed: 'Google authentication failed'
    },
    demoAccounts: 'Demo Accounts for Testing',
    demoNote: 'Click any account to auto-fill credentials'
  },
  
  // Account
  account: {
    title: 'Account Settings',
    profile: 'Profile',
    security: 'Security',
    memberSince: 'Member Since',
    email: 'Email Address',
    username: 'Username',
    fullName: 'Full Name',
    authProvider: 'Auth Provider',
    role: 'Role',
    lastLogin: 'Last Login',
    verified: 'Verified',
    edit: 'Edit',
    save: 'Save',
    changePassword: 'Change Password',
    currentPassword: 'Current Password',
    newPassword: 'New Password',
    confirmNewPassword: 'Confirm New Password',
    logout: 'Logout',
    deleteAccount: 'Delete Account',
    deleteAccountConfirm: 'Confirm Account Deletion',
    deleteAccountWarning: 'This action cannot be undone. All data will be deleted.',
    deleteConfirm: 'Delete',
    updateSuccess: 'Profile updated successfully',
    updateError: 'Failed to update profile',
    passwordChanged: 'Password changed successfully',
    passwordChangeError: 'Failed to change password',
    passwordMismatch: 'Passwords do not match',
    deleteError: 'Failed to delete account'
  },
  
  // Navigation
  nav: {
    dashboard: 'Dashboard',
    alertReduction: 'Alert Reduction',
    rules: 'Rules',
    reports: 'Reports',
    pricing: 'Pricing',
    settings: 'Settings',
    account: 'Account'
  },
  
  // Dashboard
  dashboard: {
    title: 'Dashboard',
    subtitle: 'Current status of the alert reduction system',
    
    stats: {
      reductionRate: 'Alert Reduction Rate',
      falseSuppressionRate: 'False Suppression Rate',
      processedEvents: 'Processed Events',
      activeRules: 'Active Rules',
      targetAchieved: 'Target Achieved',
      improving: 'Improving',
      safetyEnsured: 'Safety Ensured',
      last24Hours: 'Last 24 hours',
      enabled: 'Enabled'
    },
    
    charts: {
      reductionTrend: 'Reduction Trend',
      latestAlerts: 'Latest Alerts',
      reduction: 'Reduction',
      target: 'Target'
    },
    
    alerts: {
      actionRequired: 'Alerts Requiring Action',
      noUrgentAlerts: 'No urgent alerts at this time',
      openSOC: 'Open SOC Dashboard',
      checkSIEM: 'Check in SIEM',
      details: 'Details',
      count: '{{count}} alerts'
    },
    
    summary: {
      title: "Today's Summary",
      suppressedCount: 'Suppressed {{count}} alerts in the last 24 hours.',
      reductionRate: 'Reduction rate is {{rate}}%,',
      targetAchieved: 'achieving the 50% target',
      targetProgress: 'progressing toward the 50% target',
      topCategories: 'Top reduction categories:',
      events: 'events'
    }
  },
  
  // Alert Reduction
  alertReduction: {
    title: 'Alert Reduction',
    subtitle: 'Configure and run ML-based automatic reduction',
    
    settings: {
      title: 'Optimization Settings',
      targetReduction: 'Target Reduction Rate',
      targetReductionHelp: '0.6 = 60% reduction',
      epsilon: 'Epsilon (ε)',
      epsilonHelp: 'Implication detection threshold',
      fdrQ: 'FDR q-value',
      fdrQHelp: 'False discovery rate control',
      eventsPath: 'Events File Path',
      optimize: 'Run Optimization'
    },
    
    status: {
      title: 'Current Reduction Status',
      reductionRate: 'Reduction Rate',
      suppressedEvents: 'Suppressed Events',
      falseSuppressionRate: 'False Suppression Rate',
      topCategories: 'Top Reduction Categories'
    }
  },
  
  // Rules
  rules: {
    title: 'Rules Management',
    subtitle: 'Configure and manage alert reduction rules',
    newRule: 'New Rule',
    noRules: 'No rules configured',
    
    table: {
      name: 'Rule Name',
      description: 'Description',
      severity: 'Severity',
      status: 'Status',
      enabled: 'Enabled',
      disabled: 'Disabled',
      actions: 'Actions'
    },
    
    modal: {
      create: 'Create New Rule',
      edit: 'Edit Rule',
      name: 'Rule Name',
      description: 'Description',
      severity: 'Severity',
      save: 'Save',
      cancel: 'Cancel'
    }
  },
  
  // Reports
  reports: {
    title: 'Reports',
    subtitle: 'View and export daily/weekly reports',
    
    period: {
      daily: 'Daily',
      weekly: 'Weekly',
      monthly: 'Monthly'
    },
    
    summary: {
      avgReduction: 'Average Reduction',
      totalSuppressed: 'Total Suppressed',
      totalProcessed: 'Total Processed',
      last7Days: 'Last 7 days'
    },
    
    history: {
      title: 'Report History',
      date: 'Date',
      type: 'Type',
      reductionRate: 'Reduction Rate',
      processedEvents: 'Processed Events',
      suppressedAlerts: 'Suppressed Alerts',
      status: 'Status',
      completed: 'Completed',
      details: 'Details'
    },
    
    export: {
      csv: 'CSV',
      json: 'JSON',
      pdf: 'PDF',
      message: 'Export report as {{format}}'
    },
    
    chart: {
      title: 'Reduction Rate Trend',
      placeholder: 'Chart component (to be implemented with Recharts)'
    }
  },
  
  // Settings
  settings: {
    title: 'Settings',
    subtitle: 'Manage system settings and API integrations',
    save: 'Save Settings',
    saved: 'Settings saved',
    
    tabs: {
      general: 'General',
      api: 'API',
      siem: 'SIEM Integration',
      notifications: 'Notifications',
      security: 'Security'
    },
    
    general: {
      organizationName: 'Organization Name',
      timezone: 'Timezone',
      language: 'Language',
      languageHelp: 'Change the UI display language. Changes take effect immediately.'
    },
    
    api: {
      url: 'API URL',
      key: 'API Key',
      rateLimit: 'Rate Limit (req/sec)',
      timeout: 'Timeout (seconds)'
    },
    
    siem: {
      title: 'SIEM Integration Settings',
      enableSplunk: 'Enable Splunk Integration',
      enableSentinel: 'Enable Azure Sentinel Integration',
      enableOpenSearch: 'Enable OpenSearch Integration'
    },
    
    notifications: {
      email: 'Email Notifications',
      emailDesc: 'Receive important alerts via email',
      slack: 'Slack Notifications',
      slackDesc: 'Send notifications to Slack channel'
    },
    
    security: {
      mfa: 'Multi-Factor Authentication (MFA)',
      mfaDesc: 'Additional authentication at login',
      sessionTimeout: 'Session Timeout (minutes)',
      ipWhitelist: 'IP Whitelist (comma-separated)',
      auditLogRetention: 'Audit Log Retention (days)'
    }
  },
  
  // Common
  common: {
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    warning: 'Warning',
    info: 'Info',
    confirm: 'Confirm',
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    search: 'Search',
    filter: 'Filter',
    export: 'Export',
    import: 'Import',
    refresh: 'Refresh',
    actions: 'Actions'
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