/**
 * Small, inspectable BROWSER-ONLY parser for the two documented *demo-fixture* formats.
 * No upload/network call occurs here; no vendor certification is implied.
 * Separate from the Python adapter used by the local FastAPI/SQL pipeline.
 */
export const DEMO_FILES = {
  toast: ['OrderDetails.csv', 'ItemSelectionDetails.csv', 'PaymentDetails.csv'],
  square: ['orders.json', 'payments.json', 'refunds.json'],
};

const maxOrders = 2000;
function err(message) { throw new Error(message); }

export function parseCsv(input) {
  const text = input.replace(/^\uFEFF/, '');
  const rows = [];
  let row = [], value = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { value += '"'; i++; }
      else if (c === '"') quoted = false;
      else value += c;
    } else if (c === '"') {
      if (value !== '') err('Malformed CSV: quote inside unquoted field');
      quoted = true;
    } else if (c === ',') { row.push(value); value = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(value);
      if (row.some(v => v !== '')) rows.push(row);
      row = []; value = '';
    } else value += c;
  }
  if (quoted) err('Malformed CSV: unmatched quote');
  if (value !== '' || row.length) { row.push(value); rows.push(row); }
  if (!rows.length) err('CSV is empty');
  const headers = rows.shift().map(s => s.trim());
  if (new Set(headers).size !== headers.length) err('CSV has duplicate header names');
  return rows.map((cells, index) => {
    if (cells.length !== headers.length) err(`CSV row ${index + 2} has ${cells.length} fields; expected ${headers.length}`);
    return Object.fromEntries(headers.map((h, i) => [h, cells[i]]));
  });
}

function requireHeaders(rows, content, names, filename) {
  const headerLine = content.replace(/^\uFEFF/, '').split(/\r?\n/, 1)[0];
  const known = parseHeader(headerLine);
  const missing = names.filter(name => !known.includes(name));
  if (missing.length) err(`${filename}: missing required column${missing.length > 1 ? 's' : ''}: ${missing.join(', ')}`);
  return rows;
}
function parseHeader(line) { return line.split(',').map(s => s.replace(/^"|"$/g, '').trim()); }

function toCents(v, context) {
  const s = String(v ?? '').trim();
  if (!/^\d+(?:\.\d{1,2})?$/.test(s)) err(`${context}: expected a nonnegative dollar amount (e.g., 12.90), got "${s}"`);
  const [whole, fraction=''] = s.split('.');
  const amount = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(amount)) err(`${context}: amount is too large`);
  return amount;
}
function minor(v, context, optional = false) {
  if (v == null && optional) return null;
  if (!v || v.currency !== 'USD' || !Number.isSafeInteger(v.amount) || v.amount < 0) err(`${context}: expected USD with nonnegative integer cents`);
  return v.amount;
}
function validateNames(provider, inputs) {
  const required = DEMO_FILES[provider];
  if (!required) err('Unsupported source');
  const actual = Object.keys(inputs);
  const missing = required.filter(x => !(x in inputs));
  const extra = actual.filter(x => !required.includes(x));
  if (missing.length || extra.length) err(`${provider.toUpperCase()} file set invalid. ${missing.length ? 'Missing: ' + missing.join(', ') + '. ' : ''}${extra.length ? 'Unexpected: ' + extra.join(', ') : ''}`);
}
function unique(rows, key, label) {
  const ids = rows.map(x => String(x[key] ?? '').trim());
  if (ids.some(x => !x)) err(`${label}: missing ${key}`);
  if (ids.length !== new Set(ids).size) err(`${label}: duplicate ${key} values`);
}
function jsonArray(text, key, filename) {
  let parsed;
  try { parsed = JSON.parse(text); } catch (e) { err(`${filename}: invalid JSON (${e.message})`); }
  if (!parsed || !Array.isArray(parsed[key])) err(`${filename}: expected an object containing a ${key} array`);
  return parsed[key];
}

export function transformUploaded(provider, files) {
  validateNames(provider, files);
  const output = provider === 'toast' ? parseToast(files) : parseSquare(files);
  if (output.length > maxOrders) err(`Too many orders: ${output.length}; the local demonstration limit is ${maxOrders}`);
  const orderKeys = output.map(o => `${o.provider}:${o.source_order_id}`);
  if (orderKeys.length !== new Set(orderKeys).size) err('Duplicate canonical order IDs');
  return {
    provider, records: output,
    summary: {
      orders: output.length,
      items: output.reduce((s, o) => s + o.items.length, 0),
      payments: output.reduce((s, o) => s + o.payments.length, 0),
      net_sales_minor: output.reduce((s, o) => s + o.net_sales_minor, 0),
      discounts_minor: output.reduce((s, o) => s + o.discount_minor, 0),
      refunds_minor: output.reduce((s, o) => s + o.refund_minor, 0),
    },
    warnings: output.flatMap(o => o.warnings.map(message => `${o.source_order_id}: ${message}`)),
  };
}

function parseToast(files) {
  const specs = [
    ['OrderDetails.csv', ['Order Id', 'Location', 'Opened', 'Discount Amount', 'Tax', 'Tip', 'Total', 'Voided']],
    ['ItemSelectionDetails.csv', ['Order Id', 'Item Selection Id', 'Menu Item', 'Qty', 'Gross Price', 'Discnt', 'Void?']],
    ['PaymentDetails.csv', ['Order Id', 'Payment Id', 'Amount', 'Tip', 'Status', 'Refund Amount']],
  ];
  const [orders, items, payments] = specs.map(([file, columns]) => requireHeaders(parseCsv(files[file]), files[file], columns, file));
  unique(orders, 'Order Id', 'orders'); unique(items, 'Item Selection Id', 'items'); unique(payments, 'Payment Id', 'payments');
  const byItem = new Map(), byPayment = new Map();
  const allOrders = new Set(orders.map(o => o['Order Id']));
  for (const i of items) {
    if (!allOrders.has(i['Order Id'])) err(`Orphan item ${i['Item Selection Id']} references unknown order ${i['Order Id']}`);
    if (!byItem.has(i['Order Id'])) byItem.set(i['Order Id'], []);
    byItem.get(i['Order Id']).push(i);
  }
  for (const p of payments) {
    if (!allOrders.has(p['Order Id'])) err(`Orphan payment ${p['Payment Id']} references unknown order ${p['Order Id']}`);
    if (!byPayment.has(p['Order Id'])) byPayment.set(p['Order Id'], []);
    byPayment.get(p['Order Id']).push(p);
  }
  return orders.map(o => {
    const id = o['Order Id'];
    const itemRows = (byItem.get(id) ?? []).filter(x => String(x['Void?']).toLowerCase() !== 'true');
    if (!itemRows.length) err(`Toast order ${id} has no non-voided line items`);
    const itemData = itemRows.map(i => {
      const quantity = Number(i.Qty);
      if (!Number.isFinite(quantity) || quantity <= 0) err(`Order ${id}: invalid item quantity`);
      return { item_id: i['Item Selection Id'], name: i['Menu Item'], quantity, gross_minor: toCents(i['Gross Price'], `${id}: item gross`), discount_minor: toCents(i.Discnt, `${id}: item discount`) };
    });
    const paymentData = (byPayment.get(id) ?? []).map(p => ({payment_id: p['Payment Id'], amount_minor: toCents(p.Amount, `${id}: payment amount`), status: p.Status}));
    const gross = itemData.reduce((a, b) => a + b.gross_minor, 0);
    const discount = toCents(o['Discount Amount'], `${id}: order discount`);
    const refund = (byPayment.get(id) ?? []).reduce((sum, p) => sum + toCents(p['Refund Amount'] || '0', `${id}: refund`), 0);
    if (discount + refund > gross) err(`Order ${id}: discount and refunds exceed item gross`);
    const warnings = [];
    if (!paymentData.length) warnings.push('Payment coverage unknown; no matching payment rows.');
    if (itemData.reduce((s, i) => s + i.discount_minor, 0) !== discount) warnings.push('Item discounts differ from order discount; using order-level amount.');
    const expectedTotal = gross - discount + toCents(o.Tax || '0', `${id}: tax`) + toCents(o.Tip || '0', `${id}: tip`);
    if (expectedTotal !== toCents(o.Total, `${id}: reported total`)) warnings.push('Reported order total differs from calculated item/discount/tax/tip total.');
    return {provider:'toast', source_order_id:id, location_id:o.Location, created_at:o.Opened, currency:'USD', status:String(o.Voided).toLowerCase()==='true'?'VOIDED':'CLOSED', customer_id:o['GuestLift Test Customer Id']||null, gross_minor:gross, discount_minor:discount, refund_minor:refund, net_sales_minor:gross-discount-refund, tax_minor:toCents(o.Tax || '0','tax'), tip_minor:toCents(o.Tip || '0','tip'), items:itemData, payments:paymentData, lineage:{order_file:'OrderDetails.csv',item_file:'ItemSelectionDetails.csv',payment_file:'PaymentDetails.csv'}, warnings};
  });
}

function parseSquare(files) {
  const orders = jsonArray(files['orders.json'], 'orders', 'orders.json');
  const payments = jsonArray(files['payments.json'], 'payments', 'payments.json');
  const refunds = jsonArray(files['refunds.json'], 'refunds', 'refunds.json');
  unique(orders, 'id', 'Square orders'); unique(payments, 'id', 'Square payments'); unique(refunds, 'id', 'Square refunds');
  const orderIds = new Set(orders.map(o => o.id));
  const byPayment = new Map(), paymentToOrder = new Map(), byRefund = new Map();
  for (const p of payments) {
    if (!orderIds.has(p.order_id)) err(`Orphan payment ${p.id} references unknown order ${p.order_id}`);
    if (!byPayment.has(p.order_id)) byPayment.set(p.order_id, []);
    byPayment.get(p.order_id).push(p); paymentToOrder.set(p.id, p.order_id);
  }
  for (const r of refunds) {
    const id = paymentToOrder.get(r.payment_id);
    if (!id) err(`Refund ${r.id} references missing payment ${r.payment_id}`);
    if (!byRefund.has(id)) byRefund.set(id, []);
    byRefund.get(id).push(r);
  }
  return orders.map(o => {
    const id = o.id;
    if (!Array.isArray(o.line_items) || !o.line_items.length) err(`Square order ${id} missing line_items`);
    const items = o.line_items.map(i => {
      const quantity=Number(i.quantity);
      if (!Number.isFinite(quantity) || quantity<=0) err(`${id}: invalid quantity`);
      return {item_id:i.uid, name:i.name, quantity, gross_minor:minor(i.gross_sales_money, `${id}: item gross`), discount_minor:minor(i.total_discount_money,`${id}: item discount`,true) ?? 0};
    });
    const gross = items.reduce((s,i)=>s+i.gross_minor,0);
    const discount = minor(o.total_discount_money,`${id}: order discount`,true) ?? 0;
    const refund = (byRefund.get(id)??[]).filter(r=>r.status==='COMPLETED').reduce((s,r)=>s+minor(r.amount_money,`${id}: refund`),0);
    if (discount + refund > gross) err(`Square order ${id}: discounts and refunds exceed gross`);
    const payerows = byPayment.get(id)??[];
    return {provider:'square',source_order_id:id,location_id:o.location_id,created_at:o.created_at,currency:'USD',status:o.state ?? 'UNKNOWN',customer_id:o.customer_id??null,gross_minor:gross,discount_minor:discount,refund_minor:refund,net_sales_minor:gross-discount-refund,tax_minor:minor(o.total_tax_money,`${id}: tax`,true),tip_minor:minor(o.total_tip_money,`${id}: tip`,true),items,payments:payerows.map(p=>({payment_id:p.id,amount_minor:minor(p.amount_money,`${id}: payment`),status:p.status??'UNKNOWN'})),lineage:{order_file:'orders.json',payment_file:'payments.json',refund_file:'refunds.json'},warnings:payerows.length?[]:['No matching payment fixture; payment coverage unknown.']};
  });
}
