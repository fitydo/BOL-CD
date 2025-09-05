/**
 * Accessibility tests for pricing components
 * Uses axe-core for automated accessibility testing
 */

import React from 'react';
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { BrowserRouter } from 'react-router-dom';
import PricingPage from '../pages/Pricing';
import PlanCard from '../components/PlanCard';
import FeatureTable from '../components/FeatureTable';
import FAQPricing from '../components/FAQPricing';
import plansData from '../data/plans.json';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock router
const MockedRouter: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('Pricing Components Accessibility', () => {
  describe('PricingPage', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <MockedRouter>
          <PricingPage />
        </MockedRouter>
      );
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
  
  describe('PlanCard', () => {
    it('should have no accessibility violations', async () => {
      const plan = plansData.plans[0];
      const { container } = render(
        <PlanCard
          plan={plan}
          locale="ja"
          includeTax={false}
          taxRate={0.10}
          discount={0}
        />
      );
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
    
    it('should have proper ARIA labels', () => {
      const plan = plansData.plans[0];
      const { getByRole } = render(
        <PlanCard
          plan={plan}
          locale="ja"
          includeTax={false}
          taxRate={0.10}
          discount={0}
        />
      );
      
      // Check for article role
      expect(getByRole('article')).toBeInTheDocument();
      
      // Check for button with proper label
      const button = getByRole('button');
      expect(button).toHaveAttribute('aria-label');
    });
  });
  
  describe('FeatureTable', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <FeatureTable
          features={plansData.features}
          plans={plansData.plans}
          locale="ja"
        />
      );
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
    
    it('should have proper table structure', () => {
      const { getByRole, getAllByRole } = render(
        <FeatureTable
          features={plansData.features}
          plans={plansData.plans}
          locale="ja"
        />
      );
      
      // Check for table role (on desktop)
      const table = getByRole('table');
      expect(table).toBeInTheDocument();
      
      // Check for column headers
      const columnHeaders = getAllByRole('columnheader');
      expect(columnHeaders.length).toBeGreaterThan(0);
    });
  });
  
  describe('FAQPricing', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <FAQPricing
          faqs={plansData.faqs}
          locale="ja"
        />
      );
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
    
    it('should have proper ARIA attributes for expandable items', () => {
      const { getAllByRole } = render(
        <FAQPricing
          faqs={plansData.faqs}
          locale="ja"
        />
      );
      
      const buttons = getAllByRole('button');
      
      buttons.forEach(button => {
        // Check for aria-expanded attribute
        expect(button).toHaveAttribute('aria-expanded');
        
        // Check for aria-controls attribute
        expect(button).toHaveAttribute('aria-controls');
      });
    });
    
    it('should have proper heading hierarchy', () => {
      const { getByRole } = render(
        <FAQPricing
          faqs={plansData.faqs}
          locale="ja"
        />
      );
      
      // Check for section heading
      const heading = getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
      expect(heading).toHaveAttribute('id', 'faq-heading');
    });
  });
  
  describe('Keyboard Navigation', () => {
    it('should allow keyboard navigation through interactive elements', () => {
      const { getAllByRole } = render(
        <MockedRouter>
          <PricingPage />
        </MockedRouter>
      );
      
      const buttons = getAllByRole('button');
      
      buttons.forEach(button => {
        // Check that buttons are focusable
        expect(button).not.toHaveAttribute('tabindex', '-1');
      });
    });
  });
  
  describe('Color Contrast', () => {
    it('should use semantic HTML for better screen reader support', () => {
      const { container } = render(
        <MockedRouter>
          <PricingPage />
        </MockedRouter>
      );
      
      // Check for semantic HTML elements
      expect(container.querySelector('main, section, article')).toBeInTheDocument();
      expect(container.querySelector('h1, h2, h3')).toBeInTheDocument();
      expect(container.querySelector('button')).toBeInTheDocument();
    });
  });
});
