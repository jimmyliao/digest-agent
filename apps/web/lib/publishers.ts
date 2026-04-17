export interface Article {
  id: number;
  title: string;
  summary: string | null;
  source?: string;
}

export interface PublishResult {
  success: boolean;
  channel: string;
  messageCount: number;
  articlesPublished: number;
  error?: string;
}

export interface PublisherConfig {
  telegram?: { botToken: string; chatId: string };
  discord?: { webhookUrl: string };
}

function getConfig(): PublisherConfig {
  return {
    telegram: process.env.TELEGRAM_BOT_TOKEN && process.env.TELEGRAM_CHAT_ID
      ? { botToken: process.env.TELEGRAM_BOT_TOKEN, chatId: process.env.TELEGRAM_CHAT_ID }
      : undefined,
    discord: process.env.DISCORD_WEBHOOK_URL
      ? { webhookUrl: process.env.DISCORD_WEBHOOK_URL }
      : undefined,
  };
}

function isMockToken(token: string): boolean {
  return token.startsWith('test-') || token.startsWith('mock-');
}

// Format articles as text (matching Python TelegramPublisher format)
function formatArticlesText(articles: Article[]): string {
  return articles.map((a, i) =>
    `${i + 1}. **${a.title}**\n${a.summary ?? '(no summary)'}\n`
  ).join('\n');
}

// Chunk text to stay under Telegram's 4096 char limit
function chunkText(text: string, maxLen = 4000): string[] {
  if (text.length <= maxLen) return [text];
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    let end = Math.min(start + maxLen, text.length);
    // Try to break at newline
    if (end < text.length) {
      const lastNl = text.lastIndexOf('\n', end);
      if (lastNl > start) end = lastNl;
    }
    chunks.push(text.slice(start, end));
    start = end;
  }
  return chunks;
}

export async function publishTelegram(articles: Article[], config: PublisherConfig['telegram']): Promise<PublishResult> {
  if (!config) {
    return { success: false, channel: 'telegram', messageCount: 0, articlesPublished: 0, error: 'No Telegram config' };
  }

  // Mock mode
  if (isMockToken(config.botToken)) {
    console.log(`[Telegram Mock] Would publish ${articles.length} articles to chat ${config.chatId}`);
    return { success: true, channel: 'telegram', messageCount: 1, articlesPublished: articles.length };
  }

  const text = formatArticlesText(articles);
  const chunks = chunkText(text);
  let sent = 0;

  for (const chunk of chunks) {
    const res = await fetch(`https://api.telegram.org/bot${config.botToken}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: config.chatId,
        text: chunk,
        parse_mode: 'Markdown',
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      return {
        success: sent > 0,
        channel: 'telegram',
        messageCount: sent,
        articlesPublished: articles.length,
        error: `Telegram API error: ${err}`,
      };
    }
    sent++;
  }

  return { success: true, channel: 'telegram', messageCount: sent, articlesPublished: articles.length };
}

export async function publishDiscord(articles: Article[], config: PublisherConfig['discord']): Promise<PublishResult> {
  if (!config) {
    return { success: false, channel: 'discord', messageCount: 0, articlesPublished: 0, error: 'No Discord config' };
  }

  if (isMockToken(config.webhookUrl)) {
    console.log(`[Discord Mock] Would publish ${articles.length} articles`);
    return { success: true, channel: 'discord', messageCount: 1, articlesPublished: articles.length };
  }

  // Discord embeds: max 10 per message
  const BATCH = 10;
  let sent = 0;

  for (let i = 0; i < articles.length; i += BATCH) {
    const batch = articles.slice(i, i + BATCH);
    const embeds = batch.map(a => ({
      title: a.title.slice(0, 256),
      description: (a.summary ?? '').slice(0, 4096),
      color: 0x46b3a5, // LeapChat teal
      footer: { text: a.source ?? 'digest-agent' },
    }));

    const res = await fetch(config.webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ embeds }),
    });

    if (!res.ok) {
      return {
        success: sent > 0,
        channel: 'discord',
        messageCount: sent,
        articlesPublished: articles.length,
        error: `Discord webhook error: ${res.status}`,
      };
    }
    sent++;
  }

  return { success: true, channel: 'discord', messageCount: sent, articlesPublished: articles.length };
}

export async function publishAll(
  articles: Article[],
  channels: string[] = ['telegram'],
  config?: PublisherConfig
): Promise<PublishResult[]> {
  const cfg = config ?? getConfig();

  const tasks = channels.map(channel => {
    if (channel === 'telegram') return publishTelegram(articles, cfg.telegram);
    if (channel === 'discord') return publishDiscord(articles, cfg.discord);
    return Promise.resolve<PublishResult>({
      success: false, channel, messageCount: 0, articlesPublished: 0, error: `Unknown channel: ${channel}`,
    });
  });

  const results = await Promise.allSettled(tasks);
  return results.map((r, i) =>
    r.status === 'fulfilled'
      ? r.value
      : { success: false, channel: channels[i], messageCount: 0, articlesPublished: 0, error: String(r.reason) }
  );
}
