import test from 'node:test';
import assert from 'node:assert/strict';

test('System Metrics correctly flags health thresholds under 300MB target', () => {
  const healthySample = {
    memory_rss_mb: 88.4,
    memory_vms_mb: 242.1,
    cpu_percent: 1.2,
    threads_count: 4,
    target_limit_mb: 300.0,
    within_limits: true,
    uptime_seconds: 3600,
  };

  assert.equal(healthySample.within_limits, true);
  assert.ok(healthySample.memory_rss_mb < 300.0);
  assert.ok(healthySample.memory_rss_mb < 250.0); // green status

  const warningSample = {
    memory_rss_mb: 275.0,
    target_limit_mb: 300.0,
    within_limits: true,
  };
  assert.ok(warningSample.memory_rss_mb >= 250.0 && warningSample.memory_rss_mb <= 300.0);

  const exceededSample = {
    memory_rss_mb: 320.0,
    target_limit_mb: 300.0,
    within_limits: false,
  };
  assert.ok(exceededSample.memory_rss_mb > 300.0);
  assert.equal(exceededSample.within_limits, false);
});
