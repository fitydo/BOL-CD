/**
 * FAQPricing Component
 * Frequently asked questions section for pricing page
 */

import React, { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { useTranslation, type Locale } from '../lib/i18n-pricing';

interface FAQ {
  question_ja: string;
  question_en: string;
  answer_ja: string;
  answer_en: string;
}

interface FAQPricingProps {
  faqs: FAQ[];
  locale?: Locale;
}

export const FAQPricing: React.FC<FAQPricingProps> = ({
  faqs,
  locale = 'ja',
}) => {
  const { t } = useTranslation(locale);
  const isJapanese = locale === 'ja';
  const [openItems, setOpenItems] = useState<number[]>([]);
  
  const toggleItem = (index: number) => {
    setOpenItems(prev =>
      prev.includes(index)
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };
  
  return (
    <section className="mt-16" aria-labelledby="faq-heading">
      <h2 id="faq-heading" className="text-2xl font-bold text-gray-900 mb-8">
        {t.faqTitle}
      </h2>
      
      <dl className="space-y-4">
        {faqs.map((faq, index) => {
          const isOpen = openItems.includes(index);
          
          return (
            <div
              key={index}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              <dt>
                <button
                  type="button"
                  className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-gray-50 focus:outline-none focus:bg-gray-50 transition-colors"
                  onClick={() => toggleItem(index)}
                  aria-expanded={isOpen}
                  aria-controls={`faq-answer-${index}`}
                >
                  <span className="text-base font-medium text-gray-900">
                    {isJapanese ? faq.question_ja : faq.question_en}
                  </span>
                  {isOpen ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-500 flex-shrink-0 ml-2" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-500 flex-shrink-0 ml-2" />
                  )}
                </button>
              </dt>
              <dd
                id={`faq-answer-${index}`}
                className={`${isOpen ? 'block' : 'hidden'}`}
              >
                <div className="px-6 pb-4 text-sm text-gray-600">
                  {isJapanese ? faq.answer_ja : faq.answer_en}
                </div>
              </dd>
            </div>
          );
        })}
      </dl>
      
      {/* Generate structured data for SEO */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: faqs.map(faq => ({
              '@type': 'Question',
              name: isJapanese ? faq.question_ja : faq.question_en,
              acceptedAnswer: {
                '@type': 'Answer',
                text: isJapanese ? faq.answer_ja : faq.answer_en,
              },
            })),
          }),
        }}
      />
    </section>
  );
};

export default FAQPricing;
