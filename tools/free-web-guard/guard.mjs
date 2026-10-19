// Local metadata validation only. This step never authorizes any execution.
export const code = async (inputs) => {
  const fail = () => { throw new Error('INVALID_REQUEST'); };
  const shape = (value, keys) => {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) fail();
    const proto = Object.getPrototypeOf(value);
    if (proto !== Object.prototype && proto !== null) fail();
    const actual = Reflect.ownKeys(value);
    if (actual.length !== keys.length || actual.some(key => !keys.includes(key))) fail();
    for (const key of keys) {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!descriptor || !descriptor.enumerable || !('value' in descriptor)) fail();
    }
  };
  const text = (value, max) => {
    if (typeof value !== 'string' || value.length < 1 || value.length > max || !value.trim()) fail();
  };
  const isoTime = value => {
    if (typeof value !== 'string') fail();
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(Z|[+-]\d{2}:\d{2})$/.exec(value);
    if (!m) fail();
    const [, year, month, day, hour, minute, second, zone] = m;
    const leap = +year % 4 === 0 && (+year % 100 !== 0 || +year % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (+month < 1 || +month > 12 || +day < 1 || +day > days[+month - 1] || +hour > 23 || +minute > 59 || +second > 59) fail();
    if (zone !== 'Z' && (+zone.slice(1, 3) > 23 || +zone.slice(4, 6) > 59)) fail();
  };
  try {
    if (!inputs || typeof inputs !== 'object') fail();
    const descriptor = Object.getOwnPropertyDescriptor(inputs, 'request');
    if (!descriptor || !('value' in descriptor)) fail();
    const request = descriptor.value;
    shape(request, ['mode', 'evidence']);
    if (request.mode !== 'mock' && request.mode !== 'manual_web') fail();
    const evidence = request.evidence;
    if (!Array.isArray(evidence) || evidence.length > 4 || (request.mode === 'manual_web' && evidence.length < 1)) fail();
    const arrayKeys = Reflect.ownKeys(evidence);
    if (arrayKeys.length !== evidence.length + 1) fail();
    const copied = [];
    for (let i = 0; i < evidence.length; i++) {
      const itemDescriptor = Object.getOwnPropertyDescriptor(evidence, String(i));
      if (!itemDescriptor || !('value' in itemDescriptor) || !itemDescriptor.enumerable) fail();
      const item = itemDescriptor.value;
      if (request.mode === 'mock') {
        shape(item, ['fixture_id', 'summary']);
        text(item.fixture_id, 80); text(item.summary, 500);
        copied.push({ fixture_id: item.fixture_id, summary: item.summary });
      } else {
        shape(item, ['provider', 'stage', 'url', 'observed_at', 'summary']);
        if (!['gemini', 'claude'].includes(item.provider) || !['independent', 'cross'].includes(item.stage)) fail();
        const pattern = item.provider === 'gemini'
          ? /^https:\/\/gemini\.google\.com\/app\/[0-9a-f]{16}$/
          : /^https:\/\/claude\.ai\/chat\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
        if (typeof item.url !== 'string' || !pattern.test(item.url)) fail();
        isoTime(item.observed_at); text(item.summary, 500);
        copied.push({ provider: item.provider, stage: item.stage, url: item.url, observed_at: item.observed_at, summary: item.summary });
      }
    }
    const clean = { mode: request.mode, evidence: copied };
    if (JSON.stringify(clean).length > 3500) fail();
    return { ...clean, provider_execution_allowed: false, network_execution_allowed: false, evidence_status: request.mode === 'mock' ? 'synthetic' : 'caller_supplied_unverified' };
  } catch {
    throw new Error('INVALID_REQUEST');
  }
};
