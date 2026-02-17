/**
 * StockPulse v3.2 — CSV/XLS Trade Import Module
 * Parses trade files uploaded via Telegram.
 * Supports: .csv, .xlsx, .xls
 * Flexible header detection: Symbol/SYMBOL/symbol, Type/TYPE/type, etc.
 */

function parseCSVContent(content) {
    const lines = content.trim().split('\n');
    if (lines.length < 2) return { trades: [], errors: ['File is empty or has no data rows'] };

    // Parse header row (flexible matching)
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]/g, ''));
    const colMap = {
        symbol: headers.findIndex(h => ['symbol', 'stock', 'ticker', 'scrip'].includes(h)),
        type: headers.findIndex(h => ['type', 'trade_type', 'tradetype', 'action', 'side'].includes(h)),
        quantity: headers.findIndex(h => ['quantity', 'qty', 'shares', 'lots', 'volume'].includes(h)),
        price: headers.findIndex(h => ['price', 'rate', 'avg_price', 'avgprice', 'cost'].includes(h)),
        date: headers.findIndex(h => ['date', 'trade_date', 'tradedate', 'dt'].includes(h))
    };

    if (colMap.symbol === -1) return { trades: [], errors: ['Could not find Symbol column in header'] };
    if (colMap.quantity === -1) return { trades: [], errors: ['Could not find Quantity column in header'] };
    if (colMap.price === -1) return { trades: [], errors: ['Could not find Price column in header'] };

    const trades = [];
    const errors = [];

    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        const cols = line.split(',').map(c => c.trim().replace(/['"]/g, ''));

        const symbol = cols[colMap.symbol]?.toUpperCase().replace(/[^A-Z0-9&-]/g, '');
        const typeRaw = (cols[colMap.type] || 'BUY').toUpperCase();
        const type = ['BUY', 'BOUGHT', 'B'].includes(typeRaw) ? 'BUY' : ['SELL', 'SOLD', 'S'].includes(typeRaw) ? 'SELL' : null;
        const qty = parseInt(cols[colMap.quantity]);
        const price = parseFloat(cols[colMap.price]);
        const date = colMap.date >= 0 ? cols[colMap.date] : new Date().toISOString().split('T')[0];

        // Validate
        if (!symbol || symbol.length < 1 || symbol.length > 20) { errors.push(`Row ${i + 1}: Invalid symbol "${cols[colMap.symbol]}"`); continue; }
        if (!type) { errors.push(`Row ${i + 1}: Type must be BUY or SELL, got "${typeRaw}"`); continue; }
        if (isNaN(qty) || qty <= 0 || qty >= 1000000) { errors.push(`Row ${i + 1}: Invalid quantity "${cols[colMap.quantity]}"`); continue; }
        if (isNaN(price) || price <= 0 || price >= 10000000) { errors.push(`Row ${i + 1}: Invalid price "${cols[colMap.price]}"`); continue; }

        trades.push({ symbol, trade_type: type, quantity: qty, price: Math.round(price * 100) / 100, trade_date: date });
    }

    return { trades, errors };
}

function formatImportResponse(imported, errors, trades) {
    let msg = '';

    if (imported > 0) {
        msg += `✅ *Imported ${imported} trade${imported > 1 ? 's' : ''} successfully!*\n\n`;
        msg += '📋 *Summary:*\n';

        // Group by symbol
        const bySymbol = {};
        for (const t of trades) {
            if (!bySymbol[t.symbol]) bySymbol[t.symbol] = [];
            bySymbol[t.symbol].push(t);
        }
        for (const [sym, symTrades] of Object.entries(bySymbol)) {
            for (const t of symTrades) {
                msg += `• ${sym}: ${t.quantity} shares ${t.trade_type === 'BUY' ? '@' : 'SOLD @'} ₹${t.price.toLocaleString()}\n`;
            }
        }

        const totalInvested = trades.filter(t => t.trade_type === 'BUY').reduce((s, t) => s + t.quantity * t.price, 0);
        if (totalInvested > 0) msg += `\n💰 Total invested: ₹${Math.round(totalInvested).toLocaleString()}`;
    }

    if (errors.length > 0) {
        msg += `\n\n❌ *${errors.length} error${errors.length > 1 ? 's' : ''}:*\n`;
        for (const err of errors.slice(0, 5)) msg += `• ${err}\n`;
        if (errors.length > 5) msg += `• ...and ${errors.length - 5} more\n`;
    }

    if (imported === 0 && errors.length === 0) {
        msg = '📭 No trades found in the file. Make sure your CSV has columns: Symbol, Type, Quantity, Price';
    }

    return msg;
}

module.exports = { parseCSVContent, formatImportResponse };
