BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial_schema

CREATE TABLE stories (
    id VARCHAR NOT NULL, 
    title VARCHAR NOT NULL, 
    status VARCHAR NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE story_dna (
    id VARCHAR NOT NULL, 
    story_id VARCHAR NOT NULL, 
    embedding VECTOR(1536), 
    PRIMARY KEY (id), 
    FOREIGN KEY(story_id) REFERENCES stories (id) ON DELETE CASCADE
);

CREATE TABLE performance_metrics (
    id VARCHAR NOT NULL, 
    story_id VARCHAR NOT NULL, 
    metrics_data JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(story_id) REFERENCES stories (id) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema') RETURNING alembic_version.version_num;

COMMIT;

