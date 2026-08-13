const TOKEN_URL = 'https://api.ebay.com/identity/v1/oauth2/token';
const PUBLIC_KEY_URL = 'https://api.ebay.com/commerce/notification/v1/public_key/';
const OAUTH_SCOPE = 'https://api.ebay.com/oauth/api_scope';
const NOTIFICATION_PATH = '/marketplace-account-deletion';
const PUBLIC_KEY_TTL_MS = 60 * 60 * 1000;
const VERIFICATION_TOKEN_PATTERN = /^[A-Za-z0-9_-]{32,80}$/;
const tokenCache = {value: '', expiresAt: 0, fingerprint: ''};
const publicKeyCache = new Map();

const encoder = new TextEncoder();

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'}
  });
}

function bytesToBase64(bytes) {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64ToBytes(value) {
  const binary = atob(String(value || ''));
  return Uint8Array.from(binary, character => character.charCodeAt(0));
}

function decodeSignatureHeader(value) {
  const decoded = new TextDecoder('utf-8', {fatal: true}).decode(base64ToBytes(value));
  const header = JSON.parse(decoded);
  if (!header || typeof header !== 'object' || !header.kid || !header.signature) {
    throw new Error('invalid_signature_header');
  }
  const algorithm = String(header.alg || '').toLowerCase();
  const digest = String(header.digest || '').toUpperCase().replace('-', '');
  if (algorithm !== 'ecdsa' || !['SHA1', 'SHA256'].includes(digest)) {
    throw new Error('unsupported_signature_algorithm');
  }
  return {...header, algorithm, digest};
}

function pemToSpki(pem) {
  const body = String(pem || '')
    .replace(/-----BEGIN PUBLIC KEY-----/g, '')
    .replace(/-----END PUBLIC KEY-----/g, '')
    .replace(/\s+/g, '');
  if (!body) throw new Error('public_key_missing');
  return base64ToBytes(body);
}

function readDerLength(bytes, offset) {
  let length = bytes[offset++];
  if ((length & 0x80) === 0) return {length, offset};
  const count = length & 0x7f;
  if (!count || count > 2 || offset + count > bytes.length) throw new Error('invalid_der_length');
  length = 0;
  for (let index = 0; index < count; index++) length = (length << 8) | bytes[offset++];
  return {length, offset};
}

function derEcdsaToP1363(value, componentSize = 32) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let offset = 0;
  if (bytes[offset++] !== 0x30) throw new Error('invalid_der_sequence');
  const sequence = readDerLength(bytes, offset);
  offset = sequence.offset;
  if (offset + sequence.length !== bytes.length) throw new Error('invalid_der_sequence_length');

  const integers = [];
  for (let part = 0; part < 2; part++) {
    if (bytes[offset++] !== 0x02) throw new Error('invalid_der_integer');
    const integer = readDerLength(bytes, offset);
    offset = integer.offset;
    let component = bytes.slice(offset, offset + integer.length);
    offset += integer.length;
    while (component.length > componentSize && component[0] === 0) component = component.slice(1);
    if (component.length > componentSize) throw new Error('der_integer_too_large');
    const padded = new Uint8Array(componentSize);
    padded.set(component, componentSize - component.length);
    integers.push(padded);
  }
  const signature = new Uint8Array(componentSize * 2);
  signature.set(integers[0], 0);
  signature.set(integers[1], componentSize);
  return signature;
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(value));
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

async function challengeResponse(challengeCode, verificationToken, endpointUrl) {
  if (!challengeCode || !verificationToken || !endpointUrl) throw new Error('challenge_configuration_incomplete');
  return sha256Hex(`${challengeCode}${verificationToken}${endpointUrl}`);
}

function validVerificationToken(value) {
  return VERIFICATION_TOKEN_PATTERN.test(String(value || ''));
}

async function credentialFingerprint(env) {
  return sha256Hex(`${env.EBAY_CLIENT_ID || ''}\0${env.EBAY_CLIENT_SECRET || ''}`);
}

async function applicationToken(env) {
  if (!env.EBAY_CLIENT_ID || !env.EBAY_CLIENT_SECRET) throw new Error('ebay_credentials_unavailable');
  const fingerprint = await credentialFingerprint(env);
  if (tokenCache.value && tokenCache.fingerprint === fingerprint && tokenCache.expiresAt > Date.now()) return tokenCache.value;
  const basic = bytesToBase64(encoder.encode(`${env.EBAY_CLIENT_ID}:${env.EBAY_CLIENT_SECRET}`));
  const response = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: {'Authorization': `Basic ${basic}`, 'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({grant_type: 'client_credentials', scope: OAUTH_SCOPE})
  });
  if (!response.ok) throw new Error(`oauth_http_${response.status}`);
  const payload = await response.json();
  const token = String(payload.access_token || '');
  if (!token) throw new Error('oauth_token_missing');
  const expiresIn = Math.max(120, Number(payload.expires_in || 7200));
  tokenCache.value = token;
  tokenCache.fingerprint = fingerprint;
  tokenCache.expiresAt = Date.now() + Math.max(60, expiresIn - 60) * 1000;
  return token;
}

async function publicKey(keyId, env) {
  const cached = publicKeyCache.get(keyId);
  if (cached && cached.expiresAt > Date.now()) return cached.value;
  const token = await applicationToken(env);
  const response = await fetch(`${PUBLIC_KEY_URL}${encodeURIComponent(keyId)}`, {
    headers: {'Authorization': `Bearer ${token}`, 'Accept': 'application/json'}
  });
  if (!response.ok) throw new Error(`public_key_http_${response.status}`);
  const value = await response.json();
  if (!value?.key) throw new Error('public_key_missing');
  publicKeyCache.set(keyId, {value, expiresAt: Date.now() + PUBLIC_KEY_TTL_MS});
  return value;
}

async function verifyWithPublicKey(message, signatureHeader, keyResponse) {
  const header = decodeSignatureHeader(signatureHeader);
  const digest = String(keyResponse?.digest || header.digest).toUpperCase().replace('-', '');
  if (!['SHA1', 'SHA256'].includes(digest)) throw new Error('unsupported_public_key_digest');
  if (String(keyResponse?.algorithm || 'ECDSA').toUpperCase() !== 'ECDSA') throw new Error('unsupported_public_key_algorithm');
  const key = await crypto.subtle.importKey(
    'spki',
    pemToSpki(keyResponse.key),
    {name: 'ECDSA', namedCurve: 'P-256'},
    false,
    ['verify']
  );
  const derSignature = base64ToBytes(header.signature);
  const signature = derEcdsaToP1363(derSignature);
  return crypto.subtle.verify(
    {name: 'ECDSA', hash: digest === 'SHA1' ? 'SHA-1' : 'SHA-256'},
    key,
    signature,
    encoder.encode(JSON.stringify(message))
  );
}

async function verifyNotification(message, signatureHeader, env) {
  const header = decodeSignatureHeader(signatureHeader);
  const key = await publicKey(String(header.kid), env);
  return verifyWithPublicKey(message, signatureHeader, key);
}

function validDeletionMessage(message) {
  return Boolean(
    message &&
    message.metadata?.topic === 'MARKETPLACE_ACCOUNT_DELETION' &&
    message.notification?.notificationId &&
    message.notification?.data &&
    typeof message.notification.data === 'object'
  );
}

async function handleRequest(request, env) {
  const url = new URL(request.url);
  if (url.pathname === '/health' && request.method === 'GET') {
    return json({
      status: 'ok',
      component: 'genericparser-ebay-notifications',
      version: '1.9.4',
      challenge_ready: Boolean(validVerificationToken(env.EBAY_DELETION_VERIFICATION_TOKEN) && env.EBAY_DELETION_ENDPOINT_URL),
      signature_verification: 'ecdsa-public-key-api',
      persistence: 'none'
    });
  }
  if (url.pathname !== NOTIFICATION_PATH) return json({status: 'not_found'}, 404);

  if (request.method === 'GET') {
    const challengeCode = url.searchParams.get('challenge_code') || '';
    if (!challengeCode) return json({status: 'error', detail: 'challenge_code is required'}, 400);
    if (!validVerificationToken(env.EBAY_DELETION_VERIFICATION_TOKEN) || !env.EBAY_DELETION_ENDPOINT_URL) {
      return json({status: 'error', detail: 'notification endpoint is not configured'}, 503);
    }
    const response = await challengeResponse(
      challengeCode,
      env.EBAY_DELETION_VERIFICATION_TOKEN,
      env.EBAY_DELETION_ENDPOINT_URL
    );
    return json({challengeResponse: response});
  }

  if (request.method === 'POST') {
    const signature = request.headers.get('x-ebay-signature') || '';
    if (!signature) return json({status: 'invalid_signature'}, 412);
    try {
      decodeSignatureHeader(signature);
    } catch {
      return json({status: 'invalid_signature'}, 412);
    }
    let message;
    try {
      message = JSON.parse(await request.text());
    } catch {
      return json({status: 'invalid_json'}, 400);
    }
    if (!validDeletionMessage(message)) return json({status: 'invalid_notification'}, 400);
    const valid = await verifyNotification(message, signature, env);
    if (!valid) return json({status: 'invalid_signature'}, 412);
    console.log(JSON.stringify({
      ebay_account_deletion_acknowledged: {
        notification_id: String(message.notification.notificationId),
        publish_attempt_count: Number(message.notification.publishAttemptCount || 0),
        user_data_stored: false
      }
    }));
    return new Response(null, {status: 204, headers: {'Cache-Control': 'no-store'}});
  }

  return new Response(null, {status: 405, headers: {'Allow': 'GET, POST'}});
}

export default {
  async fetch(request, env) {
    try {
      return await handleRequest(request, env);
    } catch (error) {
      console.error(JSON.stringify({ebay_notification_error: String(error?.message || 'unknown_error')}));
      return json({status: 'error', detail: 'notification processing failed'}, 500);
    }
  }
};

export {
  challengeResponse,
  decodeSignatureHeader,
  derEcdsaToP1363,
  handleRequest,
  validVerificationToken,
  validDeletionMessage,
  verifyWithPublicKey
};
