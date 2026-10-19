-- 증권사 API 연결 (키움, 한국투자). 연결 하나 = 구성원 한 명의 증권사 앱키 하나.
-- 앱키·시크릿·토큰은 data_source.credential_enc 에 암호화해 저장한다 (backend/assethub/secrets.py).

ALTER TABLE data_source DROP CONSTRAINT data_source_provider_check;
ALTER TABLE data_source ADD CONSTRAINT data_source_provider_check
    CHECK (provider IN ('manual','file','kis','kiwoom','codef','upbit','krx','other'));

-- 증권사 계좌 하나는 AssetHub 계좌 하나에만 연결된다
CREATE UNIQUE INDEX account_source_ref_uniq ON account (data_source_id, external_ref)
    WHERE data_source_id IS NOT NULL AND external_ref IS NOT NULL;

-- 동기화 실행 기록
CREATE TABLE sync_run (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_source_id  bigint      NOT NULL REFERENCES data_source(id),
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          text        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running','succeeded','partial','failed')),
    summary         jsonb       NOT NULL DEFAULT '{}',
    error           text
);
CREATE INDEX ON sync_run (data_source_id, started_at DESC);
