/**
 * PlanCard Component
 * Individual pricing plan card with features, price, and CTA
 */

import React from 'react';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { formatPrice, calcMonthlyEquivalent, calculatePrice } from '../lib/pricing';
import { useTranslation, type Locale } from '../lib/i18n-pricing';

export interface PlanCardProps {
  plan: any; // Plan data from JSON
  locale?: Locale;
  includeTax?: boolean;
  taxRate?: number;
  discount?: number;
  onCtaClick?: (plan: any) => void;
}

export const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  locale = 'ja',
  includeTax = false,
  taxRate = 0.10,
  discount = 0,
  onCtaClick,
}) => {
  const { t } = useTranslation(locale);
  const isJapanese = locale === 'ja';
  
  // Calculate prices
  const annualPrice = calculatePrice({
    annual: plan.priceAnnual,
    discount,
    taxRate,
    includeTax,
  });
  
  const monthlyEquiv = calcMonthlyEquivalent(plan.priceAnnual, discount);
  const monthlyWithTax = includeTax ? Math.floor(monthlyEquiv * (1 + taxRate)) : monthlyEquiv;
  
  // Determine if this is a special card (Enterprise with custom pricing)
  const hasCustomPricing = plan.priceNote_ja || plan.priceNote_en;
  const isEnterprise = plan.slug === 'enterprise';
  const isPopular = plan.popular;
  
  return (
    <div
      className={`
        relative flex flex-col h-full
        rounded-2xl border bg-white
        transition-all duration-200
        hover:shadow-lg hover:-translate-y-1
        ${isPopular ? 'border-indigo-500 shadow-md' : 'border-gray-200'}
      `}
      role="article"
      aria-label={`${isJapanese ? plan.name_ja : plan.name_en} plan`}
    >
      {/* Popular badge */}
      {isPopular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center px-4 py-1 rounded-full text-xs font-semibold bg-indigo-500 text-white">
            {t.popular}
          </span>
        </div>
      )}
      
      {/* Card header */}
      <div className="p-6 pb-4">
        <h3 className="text-xl font-bold text-gray-900">
          {isJapanese ? plan.name_ja : plan.name_en}
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          {isJapanese ? plan.tagline_ja : plan.tagline_en}
        </p>
        <p className="mt-3 text-sm text-gray-600">
          {isJapanese ? plan.description_ja : plan.description_en}
        </p>
      </div>
      
      {/* Pricing section */}
      <div className="px-6 py-4 border-t border-gray-100">
        <div className="flex items-baseline">
          <span className="text-3xl font-bold text-gray-900">
            {hasCustomPricing ? (
              <>
                {formatPrice(annualPrice, { withCommas: true, compact: true })}
                <span className="text-lg font-normal text-gray-500 ml-1">
                  {isJapanese ? plan.priceNote_ja : plan.priceNote_en}
                </span>
              </>
            ) : (
              formatPrice(annualPrice, { withCommas: true, compact: true })
            )}
          </span>
          <span className="ml-2 text-sm text-gray-500">{t.perYear}</span>
        </div>
        
        {/* Monthly equivalent */}
        {!hasCustomPricing && (
          <div className="mt-1 text-sm text-gray-500">
            {t.monthlyEquivalent}: {formatPrice(monthlyWithTax, { withCommas: true })}
            {t.perMonth}
          </div>
        )}
        
        {/* Contract badge */}
        <div className="mt-3 inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-xs font-medium text-gray-700">
          {t.annualBilling}
        </div>
      </div>
      
      {/* Features list */}
      <div className="flex-1 px-6 py-4">
        <ul className="space-y-3" role="list">
          {(isJapanese ? plan.includes_ja : plan.includes_en)?.map((feature: string, idx: number) => (
            <li key={idx} className="flex items-start">
              <CheckIcon className="h-5 w-5 text-green-500 mt-0.5 mr-2 flex-shrink-0" aria-hidden="true" />
              <span className="text-sm text-gray-700">{feature}</span>
            </li>
          ))}
          
          {plan.excludes?.length > 0 && (
            <>
              {plan.excludes.slice(0, 2).map((feature: string, idx: number) => (
                <li key={`exclude-${idx}`} className="flex items-start opacity-50">
                  <XMarkIcon className="h-5 w-5 text-gray-400 mt-0.5 mr-2 flex-shrink-0" aria-hidden="true" />
                  <span className="text-sm text-gray-500 line-through">{feature}</span>
                </li>
              ))}
            </>
          )}
        </ul>
      </div>
      
      {/* CTA button */}
      <div className="p-6 pt-4">
        <button
          onClick={() => onCtaClick?.(plan)}
          className={`
            w-full py-3 px-4 rounded-lg font-medium
            transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-offset-2
            ${isEnterprise
              ? 'bg-gray-900 text-white hover:bg-gray-800 focus:ring-gray-900'
              : isPopular
              ? 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-600'
              : 'bg-white text-indigo-600 border-2 border-indigo-600 hover:bg-indigo-50 focus:ring-indigo-600'
            }
          `}
          aria-label={`${isJapanese ? plan.cta_ja : plan.cta_en} - ${isJapanese ? plan.name_ja : plan.name_en}`}
        >
          {isJapanese ? plan.cta_ja : plan.cta_en}
        </button>
        
        {/* Trial note for non-enterprise */}
        {!isEnterprise && (
          <p className="mt-2 text-xs text-center text-gray-500">
            {t.trialDuration}
          </p>
        )}
      </div>
    </div>
  );
};

export default PlanCard;
