/**
 * Pricing calculation utilities for BOL-CD
 * Handles annual/monthly conversion, tax calculations, and multi-year discounts
 */

export interface PricingOptions {
  annual: number;
  discount?: number; // Percentage discount (0-100)
  taxRate?: number; // Tax rate (0-1)
  includeTax?: boolean;
}

/**
 * Calculate monthly equivalent from annual price
 * @param annual - Annual price in JPY
 * @param discount - Optional discount percentage (0-100)
 * @returns Monthly equivalent price
 */
export function calcMonthlyEquivalent(annual: number, discount = 0): number {
  const discountedAnnual = annual * (1 - discount / 100);
  return Math.floor(discountedAnnual / 12);
}

/**
 * Apply tax to price
 * @param price - Base price
 * @param taxRate - Tax rate (0-1, default 0.10 for Japan)
 * @returns Price with tax
 */
export function applyTax(price: number, taxRate = 0.10): number {
  return Math.floor(price * (1 + taxRate));
}

/**
 * Calculate final price with all options
 * @param options - Pricing options
 * @returns Final calculated price
 */
export function calculatePrice(options: PricingOptions): number {
  const { annual, discount = 0, taxRate = 0.10, includeTax = false } = options;
  
  let price = annual;
  
  // Apply discount
  if (discount > 0) {
    price = price * (1 - discount / 100);
  }
  
  // Apply tax if requested
  if (includeTax) {
    price = applyTax(price, taxRate);
  }
  
  return Math.floor(price);
}

/**
 * Format price in Japanese Yen
 * @param price - Price in JPY
 * @param options - Formatting options
 * @returns Formatted price string
 */
export function formatPrice(
  price: number,
  options: { 
    withSymbol?: boolean; 
    withCommas?: boolean;
    compact?: boolean;
  } = {}
): string {
  const { withSymbol = true, withCommas = true, compact = false } = options;
  
  if (compact && price >= 1000000) {
    const millions = price / 1000000;
    const formatted = millions % 1 === 0 ? millions.toString() : millions.toFixed(1);
    return withSymbol ? `¥${formatted}M` : `${formatted}M`;
  }
  
  let formatted = price.toString();
  
  if (withCommas) {
    formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }
  
  return withSymbol ? `¥${formatted}` : formatted;
}

/**
 * Calculate price range for display
 * @param min - Minimum price
 * @param max - Maximum price
 * @param options - Formatting options
 * @returns Formatted price range string
 */
export function formatPriceRange(
  min: number,
  max: number,
  options: Parameters<typeof formatPrice>[1] = {}
): string {
  return `${formatPrice(min, options)}–${formatPrice(max, options)}`;
}

/**
 * Store tax preference in localStorage
 * @param includeTax - Whether to include tax
 */
export function saveTaxPreference(includeTax: boolean): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('pricing_include_tax', includeTax.toString());
  }
}

/**
 * Retrieve tax preference from localStorage
 * @returns Whether to include tax (default false)
 */
export function getTaxPreference(): boolean {
  if (typeof window === 'undefined') return false;
  
  const stored = localStorage.getItem('pricing_include_tax');
  return stored === 'true';
}

/**
 * Analytics event helper for pricing interactions
 * @param action - Action type
 * @param data - Event data
 */
export function trackPricingEvent(
  action: 'cta_clicked' | 'plan_viewed' | 'discount_toggled' | 'tax_toggled',
  data: Record<string, any>
): void {
  if (typeof window !== 'undefined' && 'gtag' in window) {
    (window as any).gtag('event', `pricing_${action}`, {
      event_category: 'pricing',
      ...data,
    });
  }
  
  // Also log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Analytics] pricing_${action}`, data);
  }
}

/**
 * Generate structured data for SEO
 * @param plan - Plan data
 * @param locale - Current locale
 * @returns JSON-LD structured data
 */
export function generatePlanStructuredData(
  plan: any,
  locale: string
): Record<string, any> {
  const isJapanese = locale === 'ja' || locale === 'ja-JP';
  
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: isJapanese ? plan.name_ja : plan.name_en,
    description: isJapanese ? plan.description_ja : plan.description_en,
    offers: {
      '@type': 'Offer',
      price: plan.priceAnnual,
      priceCurrency: 'JPY',
      availability: 'https://schema.org/InStock',
      priceValidUntil: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    },
  };
}
