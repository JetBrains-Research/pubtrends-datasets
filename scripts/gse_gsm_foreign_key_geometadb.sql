PRAGMA foreign_keys=off;
PRAGMA defer_foreign_keys=on;

BEGIN;

ALTER TABLE gse_gsm RENAME TO gse_gsm_old;
CREATE TABLE gse_gsm (
    gse varchar(255) NOT NULL REFERENCES gse(gse),
    gsm varchar(255) NOT NULL REFERENCES gsm(gsm),
    PRIMARY KEY (gse, gsm)
);

INSERT INTO gse_gsm (gse, gsm) SELECT DISTINCT gse, gsm FROM gse_gsm_old WHERE EXISTS(SELECT gse FROM gse WHERE gse=gse_gsm_old.gse) AND EXISTS(SELECT gsm FROM gsm WHERE gsm=gse_gsm_old.gsm);

DROP TABLE gse_gsm_old;

COMMIT;