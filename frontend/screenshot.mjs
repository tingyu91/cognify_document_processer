import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(__dirname, 'temporary screenshots');
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

const url   = process.argv[2] || 'http://localhost:3000';
const label = process.argv[3] || '';

// Auto-increment filename
const existing = fs.existsSync(dir)
  ? fs.readdirSync(dir).filter(f => f.startsWith('screenshot-')).length
  : 0;
const n    = existing + 1;
const name = label ? `screenshot-${n}-${label}.png` : `screenshot-${n}.png`;
const out  = path.join(dir, name);

const browser = await puppeteer.launch({
  headless: 'new',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
await page.screenshot({ path: out, fullPage: true });
await browser.close();

console.log('Screenshot saved:', out);
