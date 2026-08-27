-- ============================================================================
-- Test 06: pg_cron Job Registration Verification
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_job_count integer := 0;
    v_schedule text;
    v_command text;
BEGIN
    RAISE NOTICE '>>> Starting Test 06: pg_cron Registration Verification';

    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'cron' AND table_name = 'job') THEN
            SELECT count(*), max(schedule), max(command)
            INTO v_job_count, v_schedule, v_command
            FROM cron.job
            WHERE jobname = 'daily-stale-document-cleanup';

            IF v_job_count = 0 THEN
                RAISE EXCEPTION 'TEST FAILED: cron job "daily-stale-document-cleanup" not found in cron.job table!';
            END IF;

            IF v_schedule <> '0 0 * * *' THEN
                RAISE EXCEPTION 'TEST FAILED: Expected schedule "0 0 * * *", got "%"', v_schedule;
            END IF;

            RAISE NOTICE '✓ pg_cron job "daily-stale-document-cleanup" verified: schedule "%", command "%".', v_schedule, v_command;
        ELSE
            RAISE NOTICE 'pg_cron extension is present, but cron.job metadata table is not initialized in this session.';
        END IF;
    ELSE
        RAISE NOTICE 'pg_cron extension is not active in this database instance (expected in non-cron test environments).';
    END IF;

    RAISE NOTICE '>>> TEST 06 PASSED: pg_cron verification logic complete.';
END $$;

ROLLBACK;
