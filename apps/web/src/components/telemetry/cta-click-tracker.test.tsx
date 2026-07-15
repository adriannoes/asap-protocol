import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CtaClickTracker } from '@/components/telemetry/cta-click-tracker';

const trackMock = vi.hoisted(() => vi.fn());

vi.mock('@vercel/analytics', () => ({
  track: trackMock,
}));

describe('CtaClickTracker', () => {
  beforeEach(() => {
    trackMock.mockClear();
    window.history.pushState({}, '', '/features/workflow-connectors');
  });

  afterEach(() => {
    cleanup();
  });

  it('emits cta_click on primary click of [data-cta]', () => {
    render(
      <>
        <CtaClickTracker />
        <a href="https://example.com" data-cta="docs-workflow-connectors">
          Docs
        </a>
      </>
    );

    fireEvent.click(document.querySelector('[data-cta]')!);

    expect(trackMock).toHaveBeenCalledTimes(1);
    expect(trackMock).toHaveBeenCalledWith('cta_click', {
      cta: 'docs-workflow-connectors',
      path: '/features/workflow-connectors',
    });
  });

  it('emits cta_click on middle click (auxclick button 1)', () => {
    render(
      <>
        <CtaClickTracker />
        <a href="https://example.com" data-cta="docs-mcp-auth-bridge">
          Bridge
        </a>
      </>
    );

    fireEvent(
      document.querySelector('[data-cta]')!,
      new MouseEvent('auxclick', { bubbles: true, button: 1 })
    );

    expect(trackMock).toHaveBeenCalledTimes(1);
    expect(trackMock).toHaveBeenCalledWith('cta_click', {
      cta: 'docs-mcp-auth-bridge',
      path: '/features/workflow-connectors',
    });
  });

  it('resolves data-cta from a nested click target', () => {
    render(
      <>
        <CtaClickTracker />
        <a href="https://example.com" data-cta="docs-workflow-connector-example">
          <span data-testid="nested">Nested label</span>
        </a>
      </>
    );

    fireEvent.click(document.querySelector('[data-testid="nested"]')!);

    expect(trackMock).toHaveBeenCalledWith('cta_click', {
      cta: 'docs-workflow-connector-example',
      path: '/features/workflow-connectors',
    });
  });

  it('does not emit when the target has no data-cta ancestor', () => {
    render(
      <>
        <CtaClickTracker />
        <a href="https://example.com">Plain link</a>
      </>
    );

    fireEvent.click(document.querySelector('a')!);

    expect(trackMock).not.toHaveBeenCalled();
  });

  it('removes document listeners on unmount', () => {
    const { unmount } = render(<CtaClickTracker />);
    const link = document.createElement('a');
    link.href = 'https://example.com';
    link.dataset.cta = 'hero-explore-agents';
    link.textContent = 'Explore';
    document.body.appendChild(link);

    fireEvent.click(link);
    expect(trackMock).toHaveBeenCalledTimes(1);
    trackMock.mockClear();

    unmount();
    fireEvent.click(link);
    expect(trackMock).not.toHaveBeenCalled();

    link.remove();
  });
});
