PRAGMA foreign_keys=off;
PRAGMA defer_foreign_keys=on;

BEGIN;

ALTER TABLE gse RENAME TO gse_old;
CREATE TABLE gse (
	"ID" REAL,
	title TEXT,
	gse TEXT NOT NULL,
	status TEXT,
	submission_date TEXT,
	last_update_date TEXT,
	pubmed_id INTEGER,
	summary TEXT,
	type TEXT,
	contributor TEXT,
	web_link TEXT,
	overall_design TEXT,
	repeats TEXT,
	repeats_sample_list TEXT,
	variable TEXT,
	variable_description TEXT,
	contact TEXT,
	supplementary_file TEXT
);

INSERT INTO gse SELECT * FROM gse_old;

DROP TABLE gse_old;

CREATE UNIQUE INDEX idx_gse ON gse (gse);

ALTER TABLE gsm RENAME TO gsm_old;
CREATE TABLE gsm (
	"ID" REAL,
	"title" TEXT,
	"gsm" TEXT NOT NULL,
	"series_id" TEXT,
	"gpl" TEXT,
	"status" TEXT,
	"submission_date" TEXT,
	"last_update_date" TEXT,
	"type" TEXT,
	"source_name_ch1" TEXT,
	"organism_ch1" TEXT,
	"characteristics_ch1" TEXT,
	"molecule_ch1" TEXT,
	"label_ch1" TEXT,
	"treatment_protocol_ch1" TEXT,
	"extract_protocol_ch1" TEXT,
	"label_protocol_ch1" TEXT,
	"source_name_ch2" TEXT,
	"organism_ch2" TEXT,
	"characteristics_ch2" TEXT,
	"molecule_ch2" TEXT,
	"label_ch2" TEXT,
	"treatment_protocol_ch2" TEXT,
	"extract_protocol_ch2" TEXT,
	"label_protocol_ch2" TEXT,
	"hyb_protocol" TEXT,
	"description" TEXT,
	"data_processing" TEXT,
	"contact" TEXT,
	"supplementary_file" TEXT,
	"data_row_count" REAL,
	"channel_count" REAL
);

INSERT INTO gsm SELECT * FROM gsm_old;

DROP TABLE gsm_old;

CREATE UNIQUE INDEX idx_gsm ON gsm(gsm);

COMMIT;
