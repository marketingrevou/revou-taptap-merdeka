/**
 * Tap Tap Merdeka — lead capture and prize draw.
 *
 * Deploy: open the target Google Sheet > Extensions > Apps Script, paste this in,
 * then Deploy > New deployment > Web app, with
 *
 *     Execute as:      Me
 *     Who has access:  Anyone
 *
 * and paste the resulting /exec URL into LEAD_ENDPOINT at the top of index.html.
 * Re-deploy (not just save) after any edit here, or the live URL keeps the old code.
 *
 * The draw lives here rather than in the page on purpose: the prize is decided
 * once, server-side, and stored against the email. A player who replays — or
 * clears their browser, or opens an incognito window — gets the same prize back,
 * so the published odds actually hold. The page never sees the weights.
 */

const SHEET_NAME = 'leads';
const HEADERS = ['timestamp', 'email', 'variant', 'prize', 'source'];

/** Weights are relative, not percentages — they only have to be consistent. */
const PRIZES = {
  da: [
    { label: 'Early Bird 2 juta + BNSP + Exclusive Starter Kit', weight: 30 },
    { label: 'Early Bird 2 juta + BNSP', weight: 40 },
    { label: 'Early Bird 2 juta + BNSP + Exclusive AI Class Library', weight: 30 },
  ],
  swe: [
    { label: 'Early Bird 3.5 juta + 1.5 juta', weight: 10 },
    { label: 'Early Bird 3.5 juta + 1 juta', weight: 70 },
    { label: 'Early Bird 3.5 juta + 500rb', weight: 20 },
  ],
};

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

function doPost(e) {
  // Two submissions landing together must not both append a row for one email.
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
  } catch (err) {
    return json({ ok: false, error: 'busy' });
  }

  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const email = String(body.email || '').trim().toLowerCase();
    const variant = PRIZES[body.variant] ? body.variant : 'da';

    if (!EMAIL_RE.test(email)) return json({ ok: false, error: 'invalid_email' });

    const existing = findPrize(email, variant);
    if (existing) return json({ ok: true, prize: existing, returning: true });

    const prize = drawPrize(PRIZES[variant]);
    sheet().appendRow([new Date(), email, variant, prize, String(body.source || '')]);
    return json({ ok: true, prize: prize, returning: false });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

/** Health check — deliberately returns nothing about any lead. */
function doGet() {
  return json({ ok: true, service: 'taptapmerdeka', variants: Object.keys(PRIZES) });
}

function sheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
  }
  return sh;
}

/** An email may hold one prize per variant — DA and SWE are separate programs. */
function findPrize(email, variant) {
  const sh = sheet();
  const last = sh.getLastRow();
  if (last < 2) return null;
  const rows = sh.getRange(2, 2, last - 1, 3).getValues();   // email, variant, prize
  for (let i = 0; i < rows.length; i++) {
    if (String(rows[i][0]).trim().toLowerCase() === email && String(rows[i][1]) === variant) {
      return rows[i][2];
    }
  }
  return null;
}

function drawPrize(table) {
  const total = table.reduce(function (n, p) { return n + p.weight; }, 0);
  let roll = Math.random() * total;
  for (let i = 0; i < table.length; i++) {
    roll -= table[i].weight;
    if (roll < 0) return table[i].label;
  }
  return table[table.length - 1].label;   // float dust
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Run from the editor to sanity-check the weights before going live.
 * Expect roughly the configured split, ±1%.
 */
function testDistribution() {
  Object.keys(PRIZES).forEach(function (variant) {
    const tally = {};
    for (let i = 0; i < 20000; i++) {
      const p = drawPrize(PRIZES[variant]);
      tally[p] = (tally[p] || 0) + 1;
    }
    Logger.log(variant);
    Object.keys(tally).forEach(function (k) {
      Logger.log('  ' + (tally[k] / 200).toFixed(1) + '%  ' + k);
    });
  });
}
