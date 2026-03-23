'use strict';

const func = require('..').handle;
const test = require('tape');

const fixture = { log: { info: console.log } };

test('Unit: handles an HTTP GET', async t => {
  t.plan(1);
  const result = await func({ ...fixture, method: 'GET' });
  t.deepEqual(result, { body: { message: 'Hello Node World!' } });
  t.end();
});

test('Unit: handles an HTTP POST', async t => {
  t.plan(1);
  const result = await func({ ...fixture, method: 'POST' });
  t.deepEqual(result, { body: { message: 'Hello Node World!' } });
  t.end();
});

test('Unit: responds with error code if neither GET or POST', async t => {
  t.plan(1);
  const result = await func(fixture);
  t.deepEqual(result, { statusCode: 405, body: 'Method not allowed' });
  t.end();
});
