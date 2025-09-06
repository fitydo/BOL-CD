/**
 * FeatureTable Component
 * Comprehensive feature comparison table for all plans
 */

import React, { useState } from 'react';
import { CheckIcon, XMarkIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { useTranslation, type Locale } from '../lib/i18n-pricing';

interface Feature {
  key: string;
  label_ja: string;
  label_en: string;
  tooltip_ja?: string;
  tooltip_en?: string;
  plans: string[];
  notes?: Record<string, string>;
}

interface FeatureTableProps {
  features: Feature[];
  plans: any[];
  locale?: Locale;
}

export const FeatureTable: React.FC<FeatureTableProps> = ({
  features,
  plans,
  locale = 'ja',
}) => {
  const { t } = useTranslation(locale);
  const isJapanese = locale === 'ja';
  const [tooltipVisible, setTooltipVisible] = useState<string | null>(null);
  
  return (
    <div className="mt-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {t.featuresTitle}
      </h2>
      
      {/* Desktop table */}
      <div className="hidden lg:block overflow-hidden rounded-lg border border-gray-200">
        <table className="w-full" role="table">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th
                scope="col"
                className="px-6 py-4 text-left text-sm font-semibold text-gray-900"
              >
                {t.allFeatures}
              </th>
              {plans.map((plan) => (
                <th
                  key={plan.slug}
                  scope="col"
                  className="px-6 py-4 text-center text-sm font-semibold text-gray-900 min-w-[150px]"
                >
                  {isJapanese ? plan.name_ja : plan.name_en}
                  {plan.popular && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
                      {t.popular}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {features.map((feature, idx) => (
              <tr key={feature.key} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="px-6 py-4 text-sm text-gray-900">
                  <div className="flex items-center">
                    <span>{isJapanese ? feature.label_ja : feature.label_en}</span>
                    {(feature.tooltip_ja || feature.tooltip_en) && (
                      <div className="relative ml-2">
                        <button
                          type="button"
                          className="text-gray-400 hover:text-gray-600"
                          onMouseEnter={() => setTooltipVisible(feature.key)}
                          onMouseLeave={() => setTooltipVisible(null)}
                          aria-label="More information"
                        >
                          <InformationCircleIcon className="h-4 w-4" />
                        </button>
                        {tooltipVisible === feature.key && (
                          <div
                            className="absolute z-10 w-64 p-2 mt-1 text-xs text-white bg-gray-900 rounded-lg shadow-lg -left-28 top-6"
                            role="tooltip"
                          >
                            {isJapanese ? feature.tooltip_ja : feature.tooltip_en}
                            <div className="absolute w-2 h-2 bg-gray-900 transform rotate-45 -top-1 left-1/2 -translate-x-1/2" />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </td>
                {plans.map((plan) => {
                  const isIncluded = feature.plans.includes(plan.slug);
                  const note = feature.notes?.[plan.slug];
                  
                  return (
                    <td key={plan.slug} className="px-6 py-4 text-center">
                      {note ? (
                        <span className="text-sm text-gray-600">{note}</span>
                      ) : isIncluded ? (
                        <CheckIcon className="h-5 w-5 text-green-500 mx-auto" aria-label={t.included} />
                      ) : (
                        <XMarkIcon className="h-5 w-5 text-gray-300 mx-auto" aria-label={t.notIncluded} />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Mobile view */}
      <div className="lg:hidden space-y-6">
        {plans.map((plan) => (
          <div key={plan.slug} className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-4">
              {isJapanese ? plan.name_ja : plan.name_en}
              {plan.popular && (
                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
                  {t.popular}
                </span>
              )}
            </h3>
            <ul className="space-y-2">
              {features.map((feature) => {
                const isIncluded = feature.plans.includes(plan.slug);
                const note = feature.notes?.[plan.slug];
                
                return (
                  <li key={feature.key} className="flex items-start">
                    {note ? (
                      <>
                        <span className="h-5 w-5 mr-2 flex-shrink-0 text-gray-500">•</span>
                        <span className="text-sm">
                          <span className="text-gray-700">
                            {isJapanese ? feature.label_ja : feature.label_en}
                          </span>
                          <span className="text-gray-500 ml-1">({note})</span>
                        </span>
                      </>
                    ) : isIncluded ? (
                      <>
                        <CheckIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                        <span className="text-sm text-gray-700">
                          {isJapanese ? feature.label_ja : feature.label_en}
                        </span>
                      </>
                    ) : (
                      <>
                        <XMarkIcon className="h-5 w-5 text-gray-300 mr-2 flex-shrink-0" />
                        <span className="text-sm text-gray-400 line-through">
                          {isJapanese ? feature.label_ja : feature.label_en}
                        </span>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FeatureTable;
