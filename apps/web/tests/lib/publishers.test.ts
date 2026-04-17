import { describe, it, expect } from 'vitest';

describe('publishers mock mode', () => {
  it('publishTelegram with mock token returns success without a real API call', async () => {
    const { publishTelegram } = await import('../../lib/publishers');
    const result = await publishTelegram(
      [{ id: 1, title: 'Test', summary: 'Summary' }],
      { botToken: 'test-mock-token', chatId: '12345' },
    );
    expect(result.success).toBe(true);
    expect(result.channel).toBe('telegram');
    expect(result.articlesPublished).toBe(1);
  });

  it('publishDiscord with mock webhook returns success without a real API call', async () => {
    const { publishDiscord } = await import('../../lib/publishers');
    const result = await publishDiscord(
      [{ id: 1, title: 'Test', summary: 'Summary' }],
      { webhookUrl: 'test-mock-webhook' },
    );
    expect(result.success).toBe(true);
    expect(result.channel).toBe('discord');
    expect(result.articlesPublished).toBe(1);
  });

  it('publishTelegram with no config returns failure', async () => {
    const { publishTelegram } = await import('../../lib/publishers');
    const result = await publishTelegram(
      [{ id: 1, title: 'Test', summary: 'Summary' }],
      undefined,
    );
    expect(result.success).toBe(false);
    expect(result.channel).toBe('telegram');
    expect(result.error).toContain('No Telegram config');
  });

  it('publishDiscord with no config returns failure', async () => {
    const { publishDiscord } = await import('../../lib/publishers');
    const result = await publishDiscord(
      [{ id: 1, title: 'Test', summary: 'Summary' }],
      undefined,
    );
    expect(result.success).toBe(false);
    expect(result.channel).toBe('discord');
    expect(result.error).toContain('No Discord config');
  });

  it('publishAll with no config returns failure results for all channels', async () => {
    const { publishAll } = await import('../../lib/publishers');
    const results = await publishAll(
      [{ id: 1, title: 'Test', summary: 'Summary' }],
      ['telegram', 'discord'],
      { telegram: undefined, discord: undefined },
    );
    expect(results).toHaveLength(2);
    expect(results.every(r => !r.success)).toBe(true);
  });

  it('publishAll with mock configs returns success for all channels', async () => {
    const { publishAll } = await import('../../lib/publishers');
    const results = await publishAll(
      [{ id: 1, title: 'Mock Article', summary: 'Mock summary' }],
      ['telegram', 'discord'],
      {
        telegram: { botToken: 'test-bot-token', chatId: 'test-chat-id' },
        discord: { webhookUrl: 'test-discord-webhook' },
      },
    );
    expect(results).toHaveLength(2);
    expect(results.every(r => r.success)).toBe(true);
  });

  it('publishAll with unknown channel returns failure with error message', async () => {
    const { publishAll } = await import('../../lib/publishers');
    const results = await publishAll(
      [{ id: 1, title: 'Test', summary: 'Summary' }],
      ['slack'],
      {},
    );
    expect(results).toHaveLength(1);
    expect(results[0].success).toBe(false);
    expect(results[0].error).toContain('Unknown channel');
  });
});
