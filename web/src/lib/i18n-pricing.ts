/**
 * Minimal i18n dictionary for pricing page
 * Supports ja-JP and en-US locales
 */

export type Locale = 'ja' | 'en';

export const pricingI18n = {
  ja: {
    pageTitle: '料金プラン',
    pageSubtitle: '重複アラートを自動で束ね、SOCのノイズを削減。年契約でシンプルに。',
    
    // Plan terms
    annualBilling: '年契約',
    monthlyEquivalent: '月額換算',
    perYear: '/年',
    perMonth: '/月',
    startingFrom: '〜',
    
    // Contract terms
    contractLength: '契約期間',
    oneYear: '1年',
    threeYears: '3年契約',
    fiveYears: '5年契約',
    
    // Tax toggle
    taxExcluded: '税別',
    taxIncluded: '税込',
    displayPrice: '表示価格',
    
    // CTAs
    startTrial: '評価を開始',
    trialDuration: '14日間無料トライアル',
    contactSales: '営業に問い合わせ',
    discussPoC: '有償PoCを相談',
    learnMore: '詳細を見る',
    
    // Feature table
    featuresTitle: '機能比較',
    allFeatures: '全機能',
    included: '含む',
    optional: 'オプション',
    notIncluded: '対象外',
    
    // Badges
    popular: '人気',
    recommended: 'おすすめ',
    enterprise: 'エンタープライズ',
    
    // Legal/footer
    legalNote: '表示価格は税別です。年契約のみ（請求書払い / 30日サイト）。',
    trialNote: 'トライアル中はSSO/SAML無効。誤抑制保護ルール適用。',
    proofNote: '実績値は検証環境の短報に基づきます',
    
    // FAQ section
    faqTitle: 'よくある質問',
    
    // Addons
    addonsTitle: '追加オプション',
    perTenant: 'テナントあたり',
    duration: '期間',
    weeks: '週間',
  },
  
  en: {
    pageTitle: 'Pricing Plans',
    pageSubtitle: 'Automatically group duplicate alerts and reduce SOC noise. Simple annual contracts.',
    
    // Plan terms
    annualBilling: 'Annual',
    monthlyEquivalent: 'Monthly equivalent',
    perYear: '/year',
    perMonth: '/mo',
    startingFrom: 'from',
    
    // Contract terms
    contractLength: 'Contract Length',
    oneYear: '1 Year',
    threeYears: '3-Year',
    fiveYears: '5-Year',
    
    // Tax toggle
    taxExcluded: 'Tax excl.',
    taxIncluded: 'Tax incl.',
    displayPrice: 'Display price',
    
    // CTAs
    startTrial: 'Start evaluation',
    trialDuration: '14-day free trial',
    contactSales: 'Contact sales',
    discussPoC: 'Discuss PoC',
    learnMore: 'Learn more',
    
    // Feature table
    featuresTitle: 'Feature Comparison',
    allFeatures: 'All features',
    included: 'Included',
    optional: 'Optional',
    notIncluded: 'Not included',
    
    // Badges
    popular: 'Popular',
    recommended: 'Recommended',
    enterprise: 'Enterprise',
    
    // Legal/footer
    legalNote: 'Prices shown exclude tax. Annual contracts only (invoice payment / NET30).',
    trialNote: 'SSO/SAML disabled during trial. False suppression protection rules applied.',
    proofNote: 'Performance based on internal validation tests',
    
    // FAQ section
    faqTitle: 'Frequently Asked Questions',
    
    // Addons
    addonsTitle: 'Add-ons',
    perTenant: 'per tenant',
    duration: 'Duration',
    weeks: 'weeks',
  },
} as const;

/**
 * Get translation helper
 * @param locale - Current locale
 * @returns Translation function
 */
export function useTranslation(locale: Locale = 'ja') {
  return {
    t: (key: keyof typeof pricingI18n.ja): string => {
      return pricingI18n[locale][key] || pricingI18n.ja[key];
    },
    locale,
  };
}
