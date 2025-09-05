/**
 * PricingSection Component
 * Main pricing section with plans, addons, and controls
 */

import React, { useState, useEffect, useCallback } from 'react';
import { BoltIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline';
import PlanCard from './PlanCard';
import FeatureTable from './FeatureTable';
import { useTranslation, type Locale } from '../lib/i18n-pricing';
import { saveTaxPreference, getTaxPreference, trackPricingEvent, formatPrice, formatPriceRange } from '../lib/pricing';
import plansData from '../data/plans.json';

interface PricingSectionProps {
  locale?: Locale;
  onCtaClick?: (action: string, plan?: any) => void;
}

export const PricingSection: React.FC<PricingSectionProps> = ({
  locale = 'ja',
  onCtaClick,
}) => {
  const { t } = useTranslation(locale);
  const isJapanese = locale === 'ja';
  
  // State
  const [includeTax, setIncludeTax] = useState(false);
  const [selectedDiscount, setSelectedDiscount] = useState(0);
  
  // Load tax preference on mount
  useEffect(() => {
    setIncludeTax(getTaxPreference());
  }, []);
  
  // Handle tax toggle
  const handleTaxToggle = useCallback((newValue: boolean) => {
    setIncludeTax(newValue);
    saveTaxPreference(newValue);
    trackPricingEvent('tax_toggled', { include_tax: newValue, locale });
  }, [locale]);
  
  // Handle discount selection
  const handleDiscountChange = useCallback((discount: number) => {
    setSelectedDiscount(discount);
    trackPricingEvent('discount_toggled', { discount, locale });
  }, [locale]);
  
  // Handle CTA clicks
  const handlePlanCta = useCallback((plan: any) => {
    trackPricingEvent('cta_clicked', {
      plan: plan.slug,
      action: plan.cta_link,
      locale,
    });
    
    if (onCtaClick) {
      onCtaClick(plan.cta_link, plan);
    } else {
      // Default behavior: navigate to contact page
      window.location.href = plan.cta_link;
    }
  }, [locale, onCtaClick]);
  
  return (
    <div className="w-full">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {t.pageTitle}
        </h1>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          {t.pageSubtitle}
        </p>
      </div>
      
      {/* Value proof band */}
      <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-lg p-4 mb-8">
        <div className="flex items-center justify-center text-sm">
          <BoltIcon className="h-5 w-5 text-indigo-600 mr-2" />
          <span className="text-gray-700 font-medium">
            {isJapanese ? plansData.valueProof.ja : plansData.valueProof.en}
            <sup className="text-indigo-600 ml-1">[*]</sup>
          </span>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-center mb-8 space-y-4 sm:space-y-0">
        {/* Contract length selector */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600 mr-2">{t.contractLength}:</span>
          <div className="inline-flex rounded-lg border border-gray-200 p-1" role="group">
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                selectedDiscount === 0
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => handleDiscountChange(0)}
              aria-pressed={selectedDiscount === 0}
            >
              {t.oneYear}
            </button>
            {plansData.discounts.map((discount) => (
              <button
                key={discount.percent}
                type="button"
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  selectedDiscount === discount.percent
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
                onClick={() => handleDiscountChange(discount.percent)}
                aria-pressed={selectedDiscount === discount.percent}
              >
                {isJapanese ? discount.label_ja : discount.label_en}
              </button>
            ))}
          </div>
        </div>
        
        {/* Tax toggle */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">{t.displayPrice}:</span>
          <div className="inline-flex rounded-lg border border-gray-200 p-1" role="group">
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                !includeTax
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => handleTaxToggle(false)}
              aria-pressed={!includeTax}
            >
              {t.taxExcluded}
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                includeTax
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => handleTaxToggle(true)}
              aria-pressed={includeTax}
            >
              {t.taxIncluded}
            </button>
          </div>
        </div>
      </div>
      
      {/* Main plans grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
        {plansData.plans.map((plan) => (
          <PlanCard
            key={plan.slug}
            plan={plan}
            locale={locale}
            includeTax={includeTax}
            taxRate={plansData.taxRate}
            discount={selectedDiscount}
            onCtaClick={handlePlanCta}
          />
        ))}
      </div>
      
      {/* Addons section */}
      <div className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          {t.addonsTitle}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {plansData.addons.map((addon) => {
            const isPoC = addon.slug === 'poc';
            
            return (
              <div
                key={addon.slug}
                className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {isJapanese ? addon.name_ja : addon.name_en}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {isJapanese ? addon.description_ja : addon.description_en}
                    </p>
                  </div>
                  <BuildingOfficeIcon className="h-8 w-8 text-gray-400" />
                </div>
                
                {/* Pricing */}
                <div className="mb-4">
                  {isPoC && addon.priceRange ? (
                    <>
                      <div className="text-2xl font-bold text-gray-900">
                        {formatPriceRange(addon.priceRange[0], addon.priceRange[1], { compact: true })}
                      </div>
                      <div className="text-sm text-gray-500">
                        {addon.durationWeeks?.[0]}–{addon.durationWeeks?.[1]} {t.weeks}
                      </div>
                      <div className="text-xs text-indigo-600 mt-1">
                        {isJapanese ? addon.note_ja : addon.note_en}
                      </div>
                    </>
                  ) : addon.unitPriceAnnual ? (
                    <>
                      <div className="text-2xl font-bold text-gray-900">
                        {formatPrice(addon.unitPriceAnnual, { compact: true })}
                      </div>
                      <div className="text-sm text-gray-500">
                        {isJapanese ? addon.unitLabel_ja : addon.unitLabel_en}
                      </div>
                    </>
                  ) : null}
                </div>
                
                {/* Features or KPIs */}
                {(isPoC ? (isJapanese ? addon.kpis_ja : addon.kpis_en) : (isJapanese ? addon.features_ja : addon.features_en))?.map((item: string, idx: number) => (
                  <div key={idx} className="text-sm text-gray-600 mb-1">
                    • {item}
                  </div>
                ))}
                
                {/* CTA */}
                <button
                  onClick={() => handlePlanCta(addon)}
                  className="mt-4 w-full py-2 px-4 border border-indigo-600 text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors"
                >
                  {isJapanese ? addon.cta_ja : addon.cta_en}
                </button>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Feature comparison table */}
      <FeatureTable
        features={plansData.features}
        plans={plansData.plans}
        locale={locale}
      />
      
      {/* Footnotes */}
      <div className="mt-8 space-y-2 text-xs text-gray-500">
        <p>{t.legalNote}</p>
        <p>{t.trialNote}</p>
        <p>
          <sup>[*]</sup> {isJapanese ? plansData.footnotes.ja : plansData.footnotes.en}
        </p>
      </div>
    </div>
  );
};

export default PricingSection;
