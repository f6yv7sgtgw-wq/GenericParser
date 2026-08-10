import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {test} from 'node:test';

import {
  challengeResponse,
  decodeSignatureHeader,
  derEcdsaToP1363,
  handleRequest,
  validVerificationToken,
  validDeletionMessage,
  verifyWithPublicKey
} from '../src/index.js';

const signature = 'eyJhbGciOiJlY2RzYSIsImtpZCI6Ijk5MzYyNjFhLTdkN2ItNDYyMS1hMGYxLTk2Y2NiNDI4YWY0OSIsInNpZ25hdHVyZSI6Ik1FWUNJUUNmeGZJV3V4bVdjSUJRSjljNS9YN2lHREpxczJSQ0dzQkVhQWppbnlycmZBSWhBSVY2d0djVGlCdVY1S0pVaWYyaG9reXJMK1E5c3NIa2FkK214Mm5FRTI1dyIsImRpZ2VzdCI6IlNIQTEifQ==';
const message = {
  metadata: {topic: 'MARKETPLACE_ACCOUNT_DELETION', schemaVersion: '1.0', deprecated: false},
  notification: {
    notificationId: '49feeaeb-4982-42d9-a377-9645b8479411_33f7e043-fed8-442b-9d44-791923bd9a6d',
    eventDate: '2021-03-19T20:43:59.462Z',
    publishDate: '2021-03-19T20:43:59.679Z',
    publishAttemptCount: 1,
    data: {
      username: 'test_user',
      userId: 'ma8vp1jySJC',
      eiasToken: 'nY+sHZ2PrBmdj6wVnY+sEZ2PrA2dj6wJnY+gAZGEpwmdj6x9nY+seQ=='
    }
  }
};
const keyResponse = {
  key: '-----BEGIN PUBLIC KEY-----MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEZhhxXKtR+TOvtDbgTPCkSof02qgBB7IsYOyf76ilExJ/upAa/vKIKheOoCyOpcLmi4t0b4uepb7LLjmMr90FUg==-----END PUBLIC KEY-----',
  algorithm: 'ECDSA',
  digest: 'SHA1'
};

test('challenge response uses the exact eBay concatenation order', async () => {
  const challenge = 'challenge-123';
  const token = 'verification_token_123456789012345';
  const endpoint = 'https://example.workers.dev/marketplace-account-deletion';
  const expected = createHash('sha256').update(challenge).update(token).update(endpoint).digest('hex');
  assert.equal(await challengeResponse(challenge, token, endpoint), expected);
});

test('official sample signature header and ECDSA signature are accepted', async () => {
  const header = decodeSignatureHeader(signature);
  assert.equal(header.kid, '9936261a-7d7b-4621-a0f1-96ccb428af49');
  assert.equal(header.algorithm, 'ecdsa');
  assert.equal(header.digest, 'SHA1');
  assert.equal(await verifyWithPublicKey(message, signature, keyResponse), true);
});

test('DER signature is converted to the 64-byte WebCrypto format', () => {
  const decoded = decodeSignatureHeader(signature);
  const der = Uint8Array.from(Buffer.from(decoded.signature, 'base64'));
  assert.equal(derEcdsaToP1363(der).length, 64);
});

test('only marketplace account deletion messages pass schema validation', () => {
  assert.equal(validDeletionMessage(message), true);
  assert.equal(validDeletionMessage({...message, metadata: {topic: 'OTHER'}}), false);
});

test('verification token follows the eBay 32 to 80 character contract', () => {
  assert.equal(validVerificationToken('a'.repeat(32)), true);
  assert.equal(validVerificationToken('A_1-' + 'b'.repeat(28)), true);
  assert.equal(validVerificationToken('a'.repeat(31)), false);
  assert.equal(validVerificationToken('a'.repeat(81)), false);
  assert.equal(validVerificationToken('a'.repeat(31) + '!'), false);
});

test('malformed signatures receive the required precondition response', async () => {
  const request = new Request('https://example.test/marketplace-account-deletion', {
    method: 'POST',
    headers: {'x-ebay-signature': 'not-base64'},
    body: JSON.stringify(message)
  });
  const response = await handleRequest(request, {});
  assert.equal(response.status, 412);
});
