/**
 * Unit tests for pricing utilities
 */

import {
  calcMonthlyEquivalent,
  applyTax,
  calculatePrice,
  formatPrice,
  formatPriceRange,
} from '../lib/pricing';

describe('Pricing Utilities', () => {
  describe('calcMonthlyEquivalent', () => {
    it('should calculate monthly equivalent from annual price', () => {
      expect(calcMonthlyEquivalent(12000000)).toBe(1000000);
      expect(calcMonthlyEquivalent(6000000)).toBe(500000);
    });
    
    it('should apply discount correctly', () => {
      expect(calcMonthlyEquivalent(12000000, 10)).toBe(900000);
      expect(calcMonthlyEquivalent(12000000, 15)).toBe(850000);
    });
    
    it('should handle zero discount', () => {
      expect(calcMonthlyEquivalent(12000000, 0)).toBe(1000000);
    });
  });
  
  describe('applyTax', () => {
    it('should apply 10% tax by default', () => {
      expect(applyTax(1000000)).toBe(1100000);
      expect(applyTax(500000)).toBe(550000);
    });
    
    it('should apply custom tax rate', () => {
      expect(applyTax(1000000, 0.08)).toBe(1080000);
      expect(applyTax(1000000, 0.05)).toBe(1050000);
    });
    
    it('should handle zero tax rate', () => {
      expect(applyTax(1000000, 0)).toBe(1000000);
    });
  });
  
  describe('calculatePrice', () => {
    it('should calculate price with all options', () => {
      expect(calculatePrice({
        annual: 12000000,
        discount: 10,
        taxRate: 0.10,
        includeTax: true,
      })).toBe(11880000);
    });
    
    it('should calculate price without tax', () => {
      expect(calculatePrice({
        annual: 12000000,
        discount: 10,
        includeTax: false,
      })).toBe(10800000);
    });
    
    it('should handle no discount and no tax', () => {
      expect(calculatePrice({
        annual: 12000000,
      })).toBe(12000000);
    });
  });
  
  describe('formatPrice', () => {
    it('should format price with default options', () => {
      expect(formatPrice(1000000)).toBe('¥1,000,000');
      expect(formatPrice(12500000)).toBe('¥12,500,000');
    });
    
    it('should format price without symbol', () => {
      expect(formatPrice(1000000, { withSymbol: false })).toBe('1,000,000');
    });
    
    it('should format price without commas', () => {
      expect(formatPrice(1000000, { withCommas: false })).toBe('¥1000000');
    });
    
    it('should format price in compact form', () => {
      expect(formatPrice(1000000, { compact: true })).toBe('¥1M');
      expect(formatPrice(12500000, { compact: true })).toBe('¥12.5M');
      expect(formatPrice(500000, { compact: true })).toBe('¥500,000');
    });
  });
  
  describe('formatPriceRange', () => {
    it('should format price range', () => {
      expect(formatPriceRange(2000000, 3000000)).toBe('¥2,000,000–¥3,000,000');
    });
    
    it('should format price range in compact form', () => {
      expect(formatPriceRange(2000000, 3000000, { compact: true }))
        .toBe('¥2M–¥3M');
    });
    
    it('should format price range without symbols', () => {
      expect(formatPriceRange(2000000, 3000000, { withSymbol: false }))
        .toBe('2,000,000–3,000,000');
    });
  });
});
