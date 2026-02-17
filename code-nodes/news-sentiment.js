/**
 * StockPulse v3.2 — News Sentiment Module
 * Prepares news data for Claude sentiment scoring.
 * Handles NewsAPI response formatting and result parsing.
 */

function prepareNewsForScoring(newsArticles, symbols) {
    if (!newsArticles || !Array.isArray(newsArticles)) return { articles: [], query: '' };

    // Filter last 12 hours
    const twelveHoursAgo = Date.now() - 12 * 60 * 60 * 1000;
    const recent = newsArticles.filter(a => {
        const pubDate = new Date(a.publishedAt).getTime();
        return pubDate > twelveHoursAgo;
    }).slice(0, 15);

    const formatted = recent.map(a => ({
        title: a.title || '',
        source: a.source?.name || 'Unknown',
        description: (a.description || '').substring(0, 200),
        publishedAt: a.publishedAt
    }));

    return {
        articles: formatted,
        symbols: symbols,
        prompt_context: formatted.map(a => `[${a.source}] ${a.title} — ${a.description}`).join('\n')
    };
}

function parseSentimentResponse(claudeResponse) {
    try {
        const text = claudeResponse.content
            .filter(c => c.type === 'text')
            .map(c => c.text)
            .join('');
        const clean = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
        const parsed = JSON.parse(clean);

        if (!Array.isArray(parsed)) return [parsed];
        return parsed.map(item => ({
            symbol: item.symbol || 'UNKNOWN',
            sentiment_score: Math.max(-100, Math.min(100, item.sentiment_score || 0)),
            key_headline: (item.key_headline || '').substring(0, 200),
            impact: (item.impact || '').substring(0, 300),
            confidence: Math.max(0, Math.min(1, item.confidence || 0.5))
        }));
    } catch (e) {
        return [{ error: e.message, raw: claudeResponse }];
    }
}

function getSentimentEmoji(score) {
    if (score >= 60) return '🟢🟢';
    if (score >= 20) return '🟢';
    if (score >= -20) return '⚪';
    if (score >= -60) return '🔴';
    return '🔴🔴';
}

function getSentimentLabel(score) {
    if (score >= 60) return 'Very Positive';
    if (score >= 20) return 'Positive';
    if (score >= -20) return 'Neutral';
    if (score >= -60) return 'Negative';
    return 'Very Negative';
}

module.exports = { prepareNewsForScoring, parseSentimentResponse, getSentimentEmoji, getSentimentLabel };
