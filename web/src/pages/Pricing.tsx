/**
 * Pricing Page
 * Complete pricing page with all sections
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PricingSection from '../components/PricingSection';
import FAQPricing from '../components/FAQPricing';
import plansData from '../data/plans.json';

// Determine locale from browser or default to Japanese
const getLocale = (): 'ja' | 'en' => {
  if (typeof window === 'undefined') return 'ja';
  
  const browserLang = navigator.language.toLowerCase();
  if (browserLang.startsWith('en')) return 'en';
  return 'ja';
};

export default function PricingPage() {
  const navigate = useNavigate();
  const [locale] = useState<'ja' | 'en'>(getLocale());
  
  // Handle CTA clicks
  const handleCtaClick = (action: string, plan?: any) => {
    // In a real app, this would navigate to the contact page
    // For now, we'll just log it
    console.log('CTA clicked:', { action, plan });
    
    // Navigate to contact page with query params
    if (action.startsWith('/contact')) {
      navigate(action);
    }
  };
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Main pricing section */}
        <PricingSection
          locale={locale}
          onCtaClick={handleCtaClick}
        />
        
        {/* FAQ section */}
        <FAQPricing
          faqs={plansData.faqs}
          locale={locale}
        />
      </div>
      
      {/* Structured data for SEO */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'WebPage',
            name: locale === 'ja' ? '料金プラン - BOL-CD' : 'Pricing Plans - BOL-CD',
            description: locale === 'ja'
              ? '重複アラートを自動で束ね、SOCのノイズを削減。年契約でシンプルに。'
              : 'Automatically group duplicate alerts and reduce SOC noise. Simple annual contracts.',
            offers: plansData.plans.map(plan => ({
              '@type': 'Offer',
              name: locale === 'ja' ? plan.name_ja : plan.name_en,
              price: plan.priceAnnual,
              priceCurrency: 'JPY',
              availability: 'https://schema.org/InStock',
            })),
          }),
        }}
      />
    </div>
  );
}
