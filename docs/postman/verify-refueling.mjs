// Run the collection's real refueling request and its test script over HTTP.
// Minimal pm compatibility for this request only; this is not the Postman desktop runner.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';
const collection = JSON.parse(fs.readFileSync(new URL('./Spotter-Fuel-Optimizer.postman_collection.json', import.meta.url), 'utf8'));
const item = collection.item.find(item => item.name === 'Verified refueling: Indianapolis to Minneapolis');
const baseUrl = process.argv[2] || 'http://127.0.0.1:8000';
const response = await fetch(item.request.url.replace('{{base_url}}', baseUrl), {
  method: item.request.method,
  headers: Object.fromEntries(item.request.header.map(h => [h.key, h.value])),
  body: item.request.body.raw,
  signal: AbortSignal.timeout(90000),
});
const body = await response.json();
function expect(actual) {
  const chain = {
    eql: expected => assert.deepEqual(actual, expected),
    above: expected => assert.ok(actual > expected),
    below: expected => assert.ok(actual < expected),
    most: expected => assert.ok(actual <= expected),
    least: expected => assert.ok(actual >= expected),
  };
  chain.to = chain; chain.be = chain; chain.at = chain;
  return chain;
}
let passed = 0;
const pm = {
  expect,
  test: (name, test) => { test(); passed++; console.log(`PASS ${name}`); },
  response: {
    json: () => body,
    to: { have: { status: expected => assert.equal(response.status, expected) } },
  },
};
vm.runInNewContext(item.event.find(e => e.listen === 'test').script.exec.join('\n'), {pm});
console.log(JSON.stringify({tests_passed: passed, status: response.status, distance_miles:body.distance_miles, fuel_stops:body.fuel_stops.length, total_cost:body.total_cost, provider_usage:body.provider_usage}));
